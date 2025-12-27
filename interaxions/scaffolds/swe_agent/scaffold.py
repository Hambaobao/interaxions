"""
SWE Agent implementation.
"""

from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

from interaxions.scaffolds.base_scaffold import BaseScaffold, BaseScaffoldConfig
from interaxions.schemas import LiteLLMModel

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.environments.swe_bench.env import SWEBenchEnvironment
    from interaxions.schemas.job import XJob

SupportedEnvironment = Union["SWEBenchEnvironment"]

# Default templates
DEFAULT_MAIN_TEMPLATE = """#!/bin/bash
# SWE Agent Main Script
# Instance: {{ instance_id }}
# Model: {{ model }}

echo "Starting SWE Agent..."
echo "Instance ID: {{ instance_id }}"
echo "Dataset: {{ dataset }}"
echo "Model: {{ model }}"
echo "Max Iterations: {{ max_iterations }}"

# Run agent logic here
python -m sweagent.agent \\
    --model {{ model }} \\
    --instance_id {{ instance_id }} \\
    --max_iterations {{ max_iterations }} \\
    --working_dir {{ working_dir }}

echo "Agent execution completed"
"""

DEFAULT_SWEREX_SIDECAR_TEMPLATE = """#!/bin/bash
# SWE-ReX Sidecar Script
# Instance: {{ instance_id }}

echo "Starting SWE-ReX sidecar..."
echo "Instance ID: {{ instance_id }}"
echo "Dataset: {{ dataset }}"
echo "Split: {{ split }}"

# Start SWE-ReX remote server
python -m swerex.remote_runtime \\
    --instance_id {{ instance_id }} \\
    --dataset {{ dataset }} \\
    --split {{ split }} \\
    --output_dir /tmp/shared/output/

echo "SWE-ReX sidecar running..."
"""


class SWEAgentContext(BaseModel):
    """
    Context for rendering SWE-Agent main script template.
    
    This model defines all parameters required by the main.j2 template
    and provides type validation.
    """

    # From environment
    instance_id: str = Field(..., description="Environment instance ID")
    dataset: str = Field(..., description="Dataset name")
    split: str = Field(..., description="Dataset split")
    working_dir: str = Field(..., description="Working directory path")
    base_commit: str = Field(..., description="Base git commit")

    # From model
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="LLM model name")
    base_url: str = Field(..., description="LLM API base URL")
    api_key: str = Field(..., description="LLM API key")
    temperature: float = Field(..., description="LLM temperature")
    num_retries: int = Field(default=3, description="Number of retries")
    completion_kwargs: Dict[str, Any] = Field(default_factory=dict, description="LLM completion kwargs")

    # Agent runtime configuration (with sensible defaults)
    sweagent_config: str = Field(default="default", description="SWE-Agent config file name")
    tools_parse_function: str = Field(default="xml_function_call", description="Tools parse function type")
    max_iterations: int = Field(default=100, description="Maximum iterations")
    max_observation_length: int = Field(default=10000, description="Max observation length")


class SWEReXContext(BaseModel):
    """
    Context for rendering SWE-ReX sidecar script template.
    
    This model defines all parameters required by the swe-rex-sidecar.j2 template.
    """

    instance_id: str = Field(..., description="Environment instance ID")
    dataset: str = Field(..., description="Dataset name")
    split: str = Field(..., description="Dataset split")


class SWEAgentConfig(BaseScaffoldConfig):
    """
    Configuration for SWE Agent.
    
    Only contains deployment-related and structural configuration.
    Runtime parameters are defined in SWEAgentContext with defaults.
    """

    type: Literal["swe-agent"] = Field(default="swe-agent", description="The type of the agent config.")
    image: str = Field(default="ghcr.io/interaxions/swe-agent:latest", description="The Docker image to use for the agent.")
    templates: Optional[Dict[str, str]] = Field(default={
        "main": DEFAULT_MAIN_TEMPLATE,
        "swe-rex-sidecar": DEFAULT_SWEREX_SIDECAR_TEMPLATE,
    }, description="Jinja2 templates for script generation. Keys are template names, values are template strings.")


class SWEAgent(BaseScaffold):
    """
    SWE Agent for automated code tasks.
    """

    config_class = SWEAgentConfig
    config: SWEAgentConfig

    def build_context(
        self,
        model: LiteLLMModel,
        env: SupportedEnvironment,
        **kwargs,
    ) -> SWEAgentContext:
        """
        Build SWEAgentContext from model, env, and kwargs.
        
        This is a helper method to construct the context needed for task creation.
        
        Args:
            model: LLM configuration
            env: Environment instance
            **kwargs: Additional parameters (sweagent_config, max_iterations, etc.)
            
        Returns:
            SWEAgentContext instance
            
        Example:
            >>> context = agent.build_context(
            ...     model=model,
            ...     env=env,
            ...     sweagent_config='default.yaml',
            ...     max_iterations=10,
            ...     # ... other params
            ... )
        """
        return SWEAgentContext(
            # From environment
            instance_id=env.environment_id,
            dataset=env.dataset,
            split=env.split,
            working_dir=env.working_dir,
            base_commit=env.base_commit,
            # From model
            provider=model.provider,
            model=model.model,
            base_url=model.base_url,
            api_key=model.api_key,
            temperature=model.temperature,
            # Runtime configuration (use kwargs or defaults from Context)
            sweagent_config=kwargs.get('sweagent_config', 'default.yaml'),
            tools_parse_function=kwargs.get('tools_parse_function', 'xml_function_call'),
            max_iterations=kwargs.get('max_iterations', 100),
            max_observation_length=kwargs.get('max_observation_length', 10000),
            # Optional parameters
            completion_kwargs=kwargs.get('completion_kwargs', {}),
            num_retries=kwargs.get('num_retries', 3),
        )

    def create_task(self, job: "XJob", **kwargs: Any) -> "Task":
        """
        Create an Argo Workflows task for SWE Agent from an XJob specification.
        
        Loads environment and builds execution context from the job specification.
        
        Args:
            job: XJob protocol containing all required configuration.
                 Extracts:
                 - job.model: LLM configuration
                 - job.scaffold.params: Scaffold-specific parameters (sweagent_config, max_iterations, etc.)
                 - job.environment: Environment specification for loading
                 - job.environment.environment_id: For task naming
            **kwargs: Additional container configuration options.
            
        Returns:
            Hera Task with Container template.
            
        Example:
            >>> from interaxions.schemas import XJob, Scaffold, Environment, ...
            >>> from interaxions.hub import AutoScaffold
            >>> 
            >>> job = XJob(
            ...     model=LiteLLMModel(...),
            ...     scaffold=Scaffold(
            ...         repo_name_or_path="swe-agent",
            ...         params={
            ...             "sweagent_config": "default.yaml",
            ...             "max_iterations": 10
            ...         }
            ...     ),
            ...     environment=Environment(
            ...         repo_name_or_path="swe-bench",
            ...         environment_id="django__django-12345",
            ...         source="hf",
            ...         params={"dataset": "princeton-nlp/SWE-bench", "split": "test"}
            ...     ),
            ...     ...
            ... )
            >>> 
            >>> scaffold = AutoScaffold.from_repo("swe-agent")
            >>> task = scaffold.create_task(job)
            >>> # task.name = "sweagent-{environment_id}"
        """
        from hera.workflows import Container, Env, EmptyDirVolume, OSSArtifact, Task
        from hera.workflows.models import VolumeMount
        from interaxions.hub import AutoEnvironment

        env = AutoEnvironment.from_repo(
            repo_name_or_path=job.environment.repo_name_or_path,
            environment_id=job.environment.environment_id,
            source=job.environment.source,
            revision=job.environment.revision,
            **job.environment.params,
        )

        # Build context from job
        context = self.build_context(
            model=job.model,
            env=env,
            **job.scaffold.params,
        )

        # Auto-generate name from job
        name = f"sweagent-{job.environment.environment_id}"

        # define inputs and outputs
        inputs = [
            OSSArtifact(
                name="predictions",
                path="/workspace/predictions.json",
                key="...",
            ),
        ]
        outputs = [
            OSSArtifact(
                name="results",
                path="/output/evaluation",
                key="...",
            ),
        ]

        # Render main execution script using context
        main_script = self.render_template("main", context.model_dump())

        # Create sidecars if needed
        sidecars = []
        if self.config.templates and "swe-rex-sidecar" in self.config.templates:
            sidecar_context = SWEReXContext(
                instance_id=context.instance_id,
                dataset=context.dataset,
                split=context.split,
            )
            sidecars.append(self.create_swerex_sidecar(sidecar_context))

        # Create container
        container = Container(
            labels={
                "task-type": "rollout",
                "task-name": "sweagent"
            },
            name=f"{name}-sweagent",
            image=self.config.image,
            image_pull_policy=job.runtime.image_pull_policy,
            command=["bash", "-c", main_script],
            inputs=inputs,
            outputs=outputs,
            env=[
                Env(name="OUTPUT_DIR", value="/tmp/shared/output/"),
                Env(name="CONFIG_DICT_PATH", value="/tmp/shared/output/config_dict.json"),
            ],
            sidecars=sidecars if sidecars else None,
            volumes=[
                EmptyDirVolume(name="shared-volume", mount_path="/tmp/shared/"),
            ],
            volume_mounts=[
                VolumeMount(name="result-volume", mount_path="/tmp/shared/output/"),
            ],
        )

        return Task(name=name, template=container)

    def create_swerex_sidecar(self, context: SWEReXContext):
        """
        Create SWE-ReX sidecar container from context.
        
        Args:
            context: SWEReXContext with sidecar parameters.
            
        Returns:
            UserContainer for sidecar.
        """
        from hera.workflows import UserContainer
        from hera.workflows.models import VolumeMount

        # Render sidecar script
        sidecar_script = self.render_template("swe-rex-sidecar", context.model_dump())

        return UserContainer(
            name="swerex-remote",
            image=self.config.image,
            image_pull_policy="IfNotPresent",
            command=["bash", "-c", sidecar_script],
            volume_mounts=[
                VolumeMount(
                    name="shared-volume",
                    mount_path="/tmp/shared/",
                    read_only=False,
                ),
            ],
        )
