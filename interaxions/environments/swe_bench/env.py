"""
SWE-Bench environment implementation.
"""

import json

from typing import TYPE_CHECKING, List, Literal, Optional, Union

from pydantic import Field

from interaxions.environments.base_environment import (
    BaseEnvironmentFactory,
    BaseEnvironmentConfig,
    BaseEnvironment,
)

if TYPE_CHECKING:
    from hera.workflows import OSSArtifact, S3Artifact, GCSArtifact
    from hera.workflows import Task

# Argo Workflows Artifact types
ArgoArtifact = Union["OSSArtifact", "S3Artifact", "GCSArtifact"]


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

    verify_template: str = Field(..., description="Verification script template")

    def create_task(
        self,
        name: str,
        predictions_path: str = "gold",
        inputs: Optional[List[ArgoArtifact]] = None,
        outputs: Optional[List[ArgoArtifact]] = None,
        **kwargs,
    ) -> "Task":
        """
        Create an Argo Workflow task for evaluating this environment instance.
        
        Args:
            name: Task name
            predictions_path: Path to predictions file (default: "gold")
            inputs: List of Argo Artifact objects (OSSArtifact, S3Artifact, GCSArtifact)
            outputs: List of Argo Artifact objects (OSSArtifact, S3Artifact, GCSArtifact)
            **kwargs: Additional arguments for the task.
            
        Returns:
            Hera Task for Argo Workflows
            
        Example:
            >>> from hera.workflows import OSSArtifact
            >>> from hera.workflows.models import SecretKeySelector
            >>> 
            >>> # Create artifacts using Hera directly
            >>> storage_kwargs = {
            ...     "endpoint": "oss-cn-hangzhou.aliyuncs.com",
            ...     "bucket": "my-bucket",
            ...     "access_key_secret": SecretKeySelector(name="oss-creds", key="accessKey"),
            ...     "secret_key_secret": SecretKeySelector(name="oss-creds", key="secretKey")
            ... }
            >>> inputs = [OSSArtifact(name="predictions", path="/workspace/predictions.json", key="...", **storage_kwargs)]
            >>> outputs = [OSSArtifact(name="results", path="/output/evaluation", key="...", **storage_kwargs)]
            >>> 
            >>> # Create evaluation task
            >>> factory = SWEBenchFactory.from_pretrained("ix-hub/swe-bench")
            >>> env = factory.get_from_hf(
            ...     environment_id="django__django-12345",
            ...     dataset="princeton-nlp/SWE-bench",
            ...     split="test"
            ... )
            >>> task = env.create_task(
            ...     name="eval-django-12345",
            ...     predictions_path="/workspace/predictions.json",
            ...     inputs=inputs,
            ...     outputs=outputs
            ... )
        """
        from hera.workflows import Container
        from jinja2 import Template

        # Render verification template with all parameters
        verify_template = Template(self.verify_template)
        verify_script = verify_template.render(
            dataset=self.dataset,
            split=self.split,
            instance_id=self.environment_id,
            predictions_path=predictions_path,
            output_dir="/output",  # Fixed output directory
        )

        # Create Argo container
        container = Container(
            name=name,
            image=self.docker_image,
            command=["/bin/bash", "-c", verify_script],
            inputs=inputs,
            outputs=outputs,
        )

        return Task(name=name, template=container)


class SWEBenchConfig(BaseEnvironmentConfig):
    """Configuration for SWE-Bench Environment."""

    type: Literal["swe-bench"] = "swe-bench"


class SWEBenchFactory(BaseEnvironmentFactory):
    """
    SWE-Bench environment factory (configuration manager + factory).
    
    Use from_pretrained() to load configuration, then use get_from_hf() or get_from_oss()
    to create specific environment instances.
    
    Example:
        >>> # Load factory (configuration + templates)
        >>> factory = SWEBenchFactory.from_pretrained("ix-hub/swe-bench")
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
        >>> # Create evaluation tasks
        >>> task1 = env1.create_task(name="eval-django", predictions_path="/workspace/predictions.json")
        >>> task2 = env2.create_task(name="eval-flask", predictions_path="/workspace/predictions.json")
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
            >>> factory = SWEBenchFactory.from_pretrained("ix-hub/swe-bench")
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
            verify_template=self.config.templates["verify"],
        )

    def get_from_oss(
        self,
        environment_id: str,
        dataset: str,
        split: str,
        oss_endpoint: str,
        oss_access_key_id: str,
        oss_access_key_secret: str,
        oss_region: str,
        revision: Optional[str] = None,
    ) -> SWEBenchEnvironment:
        """
        Get a SWE-Bench environment instance from OSS storage using ossdata.
        
        Args:
            environment_id: Unique environment/instance identifier
            dataset: Dataset name
            split: Dataset split
            oss_endpoint: OSS endpoint (e.g., "oss-cn-hangzhou.aliyuncs.com")
            oss_access_key_id: OSS access key ID
            oss_access_key_secret: OSS secret access key
            oss_region: OSS region
            revision: Dataset revision/version (optional)
            
        Returns:
            SWEBenchEnvironment instance
            
        Example:
            >>> factory = SWEBenchFactory.from_pretrained("ix-hub/swe-bench")
            >>> env = factory.get_from_oss(
            ...     environment_id="django__django-12345",
            ...     dataset="princeton-nlp/SWE-bench",
            ...     split="test",
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
        )
