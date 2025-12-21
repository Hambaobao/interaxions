"""
SWE Agent implementation.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from interaxions.agents.base_agent import BaseAgent, BaseAgentConfig
from interaxions.agents.models import LLM

if TYPE_CHECKING:
    from hera.workflows import OSSArtifact, S3Artifact, GCSArtifact, Task
    from interaxions.environments.swe_bench.env import SWEBenchEnvironment

SupportedEnvironment = Union["SWEBenchEnvironment"]
ArgoArtifact = Union["OSSArtifact", "S3Artifact", "GCSArtifact"]

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


class SWEAgentConfig(BaseAgentConfig):
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


class SWEAgent(BaseAgent):
    """
    SWE Agent for automated code tasks.
    """

    config_class = SWEAgentConfig
    config: SWEAgentConfig

    def build_context(
        self,
        model: LLM,
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

    def create_task(
        self,
        name: str,
        *,
        context: SWEAgentContext,
        inputs: Optional[List[ArgoArtifact]] = None,
        outputs: Optional[List[ArgoArtifact]] = None,
        image_pull_policy: Literal["Always", "IfNotPresent"] = "IfNotPresent",
        **kwargs: Any,
    ) -> "Task":
        """
        Create an Argo Workflows task for SWE Agent.
        
        This method creates a task from a pre-built context. Use build_context()
        to construct the context from model, env, and kwargs.
        
        Args:
            name: Task name.
            
        Required keyword arguments:
            context: SWEAgentContext with all required parameters.
            
        Optional keyword arguments:
            inputs: List of Argo Artifact objects (OSSArtifact, S3Artifact, GCSArtifact).
            outputs: List of Argo Artifact objects (OSSArtifact, S3Artifact, GCSArtifact).
            image_pull_policy: Image pull policy ("Always" or "IfNotPresent").
            **kwargs: Additional container configuration options.
            
        Returns:
            Hera Task with Container template.
        
        Example:
            >>> from interaxions.agents.swe_agent import SWEAgent
            >>> from interaxions.agents import LLM
            >>> 
            >>> agent = SWEAgent.from_repo("swe-agent")
            >>> 
            >>> # Build context
            >>> context = agent.build_context(
            ...     model=LLM(provider="openai", model="gpt-4", ...),
            ...     env=env,
            ...     sweagent_config='default.yaml',
            ...     tools_parse_function='python',
            ...     max_iterations=10,
            ...     max_observation_length=1000,
            ... )
            >>> 
            >>> # Create task from context
            >>> task = agent.create_task(
            ...     name="swe-task",
            ...     context=context,
            ...     inputs=inputs,
            ...     outputs=outputs,
            ... )
        """
        from hera.workflows import Container, Task, Env, EmptyDirVolume
        from hera.workflows.models import VolumeMount

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
            image_pull_policy=image_pull_policy,
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
