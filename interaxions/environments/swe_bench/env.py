"""
SWE-Bench environment implementation.
"""

import json

from typing import Any, Dict, Literal, Optional

from pydantic import Field

from hera.workflows import (
    Container,
    UserContainer,
    OSSArtifact,
    Task,
    TarArchiveStrategy,
    Env,
    Resources,
)
from hera.workflows.models import SecurityContext
from jinja2 import Template

from interaxions.schemas import XJob
from interaxions.environments.base_environment import (
    BaseEnvironmentFactory,
    BaseEnvironmentConfig,
    BaseEnvironment,
)
# Default templates
DEFAULT_VERIFY_TEMPLATE = """
#!/bin/bash

echo "=== SWE-Bench Evaluation Started ==="
echo "Dataset: {{ dataset }}"
echo "Split: {{ split }}"
echo "Instance ID: {{ instance_id }}"

mkdir -p $OUTPUT_DIR/evaluation

# Wait for Docker daemon to be ready
if [ "$USE_DIND" = "1" ]; then
    echo "Waiting for Docker daemon to be ready..."
    while ! docker info > /dev/null 2>&1; do
        sleep 1
    done
    echo "Docker daemon is ready"
fi

# Verify input files exist
echo "=== Verifying Input Files ==="

if [ "{{ predictions_path }}" = "gold" ] || [ -f "{{ predictions_path }}" ]; then

    echo "Predictions file is gold or found: {{ predictions_path }}"
    echo "=== Running SWE-Bench Evaluation ==="
    conda run -n swe-evaluation swe-eval \
        --dataset "{{ dataset }}" \
        --split "{{ split }}" \
        --instance-id "{{ instance_id }}" \
        --predictions-path "{{ predictions_path }}" \
        --output-dir "$OUTPUT_DIR/evaluation"
else
    echo "Predictions file is not gold and not found: {{ predictions_path }}"
fi
"""


class SWEBenchEnvironment(BaseEnvironment):
    """
    A specific SWE-Bench environment instance.
    
    This represents one specific task/problem from the dataset
    (e.g., django__django-12345 with its problem_statement, base_commit, etc.).
    """

    dataset: str = Field(..., description="Dataset name")
    split: str = Field(..., description="Dataset split")
    language: str = Field(..., description="Programming language")
    problem_statement: str = Field(..., description="Problem statement")
    working_dir: str = Field(..., description="Working directory")
    base_commit: str = Field(..., description="Base git commit")
    docker_image: str = Field(..., description="Docker image")

    # Optional parameters for verification
    verify_image: Optional[str] = Field(default=None, description="Verification docker image")
    verify_template: Optional[str] = Field(default=None, description="Verification script template")

    def create_dind_sidecar(self, job: "XJob", **kwargs: Any) -> "Task":
        """
        Create a dind sidecar container for the SWE-bench container.
        """
        return UserContainer(
            name="docker-daemon",
            image="docker:dind",
            security_context=SecurityContext(privileged=True),
            env=[Env(name="DOCKER_TLS_CERTDIR", value="")],
            command=["dockerd-entrypoint.sh"],
            args=["--tls=false", "--host=tcp://0.0.0.0:2375"],
            resources=Resources(cpu_request=3, memory_request="4Gi"),
        )

    def create_task(self, job: "XJob", **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow task for evaluating this environment instance from an XJob specification.
        
        Extracts environment configuration from the job.
        
        Args:
            job: XJob protocol containing environment params and runtime config.
                 Extracts:
                 - job.environment.params: Environment-specific parameters (e.g., predictions_path)
                 - job.environment.environment_id: For task naming
            **kwargs: Additional container configuration options.
            
        Returns:
            Hera Task for Argo Workflows.
            
        Example:
            >>> from interaxions.schemas import XJob, Environment, ...
            >>> from interaxions.hub import AutoEnvironmentFactory
            >>> 
            >>> job = XJob(
            ...     environment=Environment(
            ...         repo_name_or_path="swe-bench",
            ...         environment_id="django__django-12345",
            ...         source="hf",
            ...         params={
            ...             "dataset": "princeton-nlp/SWE-bench",
            ...             "split": "test",
            ...             "predictions_path": "/workspace/predictions.json"
            ...         }
            ...     ),
            ...     ...
            ... )
            >>> 
            >>> factory = AutoEnvironmentFactory.from_repo("swe-bench")
            >>> env = factory.get_from_hf(...)
            >>> task = env.create_task(job)
            >>> # task.name = "env-{environment_id}"
        """

        # Extract parameters from job
        predictions_path = job.environment.params.get('predictions_path', '/tmp/output/output.sweb.jsonl')

        # define inputs and outputs
        inputs = [
            OSSArtifact(
                name="rollout-result",
                path="/tmp/output/",
                # ... other parameters ...
                archive=TarArchiveStrategy(),
            )
        ]
        outputs = [
            OSSArtifact(
                name="evaluation-result",
                path="/tmp/output/",
                # ... other parameters ...
                archive=TarArchiveStrategy(),
            )
        ]

        # Render verification template with all parameters
        verify_template = Template(self.verify_template)
        verify_script = verify_template.render(
            dataset=self.dataset,
            split=self.split,
            instance_id=self.environment_id,
            predictions_path=predictions_path,
            output_dir="/tmp/output/",  # Fixed output directory
        )
        sidecars = [self.create_dind_sidecar(job)]

        # Create Argo container
        container = Container(
            name=f"swe-bench",
            image=self.verify_image,
            command=["/bin/bash", "-c", verify_script],
            inputs=inputs,
            outputs=outputs,
            env=[
                Env(name="DOCKER_HOST", value="tcp://localhost:2375"),
                # ... other environment variables ...
            ],
            resources=Resources(cpu_request=2, memory_request="8Gi"),
            sidecars=sidecars,
        )

        return Task(name="swe-bench-verify", template=container)


class SWEBenchConfig(BaseEnvironmentConfig):
    """Configuration for SWE-Bench Environment."""

    type: Literal["swe-bench"] = "swe-bench"
    images: Dict[str, str] = Field(default={
        "swe-bench": "swe-bench:swe-evaluation",
    }, description="Docker images for SWE-bench")
    templates: Dict[str, str] = Field(default={
        "verify": DEFAULT_VERIFY_TEMPLATE,
    }, description="Jinja2 templates for verification scripts")


class SWEBenchFactory(BaseEnvironmentFactory):
    """
    SWE-Bench environment factory (configuration manager + factory).
    
    Use from_repo() to load configuration, then use get_from_hf() or get_from_oss()
    to create specific environment instances.
    
    Example:
        >>> # Load factory (configuration + templates)
        >>> factory = SWEBenchFactory.from_repo("ix-hub/swe-bench")
        >>> 
        >>> # Create environment instances
        >>> env1 = factory.get_from_hf(
        ...     environment_id="django__django-12345",
        ...     dataset="princeton-nlp/SWE-bench",
        ...     split="test"
        ... )
        >>> env2 = factory.get_from_hf(
        ...     environment_id="flask__flask-1234",
        ...     dataset="princeton-nlp/SWE-bench",
        ...     split="test"
        ... )
        >>> 
        >>> # Create evaluation tasks (simplified API)
        >>> task1 = env1.create_task(predictions_path="/workspace/predictions.json")
        >>> task2 = env2.create_task(predictions_path="/workspace/predictions.json")
    """

    config_class = SWEBenchConfig
    config: SWEBenchConfig

    def get_from_hf(
        self,
        environment_id: str,
        dataset: str,
        split: str,
        revision: Optional[str] = None,
        token: Optional[str] = None,
        **kwargs: Any,
    ) -> SWEBenchEnvironment:
        """
        Get a SWE-Bench environment instance from HuggingFace dataset.
        
        Args:
            environment_id: Unique environment/instance identifier
            dataset: Dataset name
            split: Dataset split
            revision: Dataset revision/version
            token: HuggingFace token
        Returns:
            SWEBenchEnvironment instance
            
        Example:
            >>> factory = SWEBenchFactory.from_repo("ix-hub/swe-bench")
            >>> env = factory.get_from_hf(
            ...     environment_id="django__django-12345",
            ...     dataset="princeton-nlp/SWE-bench",
            ...     split="test"
            ... )
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError("HuggingFace datasets library is required. "
                              "Install it with: pip install interaxions[hf]")

        # Load dataset and find instance
        dataset_obj = load_dataset(dataset, split=split, revision=revision, token=token)
        items = dataset_obj.filter(lambda x: x["instance_id"] == environment_id)

        if len(items) == 0:
            raise ValueError(f"Environment with id {environment_id} not found in {dataset}")

        item = items[0]

        return SWEBenchEnvironment(
            environment_id=environment_id,
            dataset=dataset,
            split=split,
            language=item.get("language", "python"),
            problem_statement=item.get("problem_statement", ""),
            working_dir=item.get("workdir", "/testbed"),
            base_commit=item["base_commit"],
            docker_image=item.get("docker_image", f"swe-bench:{environment_id}"),
            verify_image=self.config.images["swe-bench"],
            verify_template=self.config.templates["verify"],
        )

    def get_from_oss(
        self,
        environment_id: str,
        dataset: str,
        split: str,
        oss_region: str,
        oss_endpoint: str,
        oss_access_key_id: str,
        oss_access_key_secret: str,
        revision: Optional[str] = None,
        **kwargs: Any,
    ) -> SWEBenchEnvironment:
        """
        Get a SWE-Bench environment instance from OSS storage using ossdata.
        
        Args:
            environment_id: Unique environment/instance identifier
            dataset: Dataset name
            split: Dataset split
            oss_region: OSS region
            oss_endpoint: OSS endpoint (e.g., "oss-cn-hangzhou.aliyuncs.com")
            oss_access_key_id: OSS access key ID
            oss_access_key_secret: OSS secret access key
            revision: Dataset revision/version (optional)
            
        Returns:
            SWEBenchEnvironment instance
            
        Example:
            >>> factory = SWEBenchFactory.from_repo("ix-hub/swe-bench")
            >>> env = factory.get_from_oss(
            ...     environment_id="django__django-12345",
            ...     dataset="princeton-nlp/SWE-bench",
            ...     split="test",
            ...     oss_region="cn-hangzhou",
            ...     oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
            ...     oss_access_key_id="your-key-id",
            ...     oss_access_key_secret="your-secret-key"
            ... )
        """
        try:
            import ossdata
        except ImportError:
            raise ImportError("ossdata library is required. "
                              "Install it with: pip install interaxions[oss]")

        # Load from OSS
        # Note: version format is "split" or "split@revision"
        version = f"{split}@{revision}" if revision else split
        item = json.loads(ossdata.get_item(
            name=dataset,
            version=version,
            instance_id=environment_id,
            oss_access_key_id=oss_access_key_id,
            oss_access_key_secret=oss_access_key_secret,
            oss_endpoint=oss_endpoint,
            oss_region=oss_region,
        ))

        return SWEBenchEnvironment(
            environment_id=environment_id,
            dataset=dataset,
            split=split,
            language=item.get("language", "python"),
            problem_statement=item["problem_statement"],
            working_dir=item.get("workdir", "/testbed"),
            base_commit=item["base_commit"],
            docker_image=item["docker_image"],
            verify_template=self.config.templates["verify"],
            verify_image=self.config.images["swe-bench"],
        )
