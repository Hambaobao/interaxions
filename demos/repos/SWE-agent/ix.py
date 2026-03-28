"""
SWE-Agent task implementation.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from hera.workflows import (
    Container,
    UserContainer,
    Env,
    EmptyDirVolume,
    OSSArtifact,
    Task,
    TarArchiveStrategy,
    Resources,
)
from hera.workflows.models import VolumeMount

from interaxions.tasks.base_task import BaseTask, BaseTaskConfig


class SWEAgentConfig(BaseTaskConfig):
    """Configuration for SWE-Agent, loaded from config.yaml."""

    type: Literal["swe-agent"] = Field(default="swe-agent")
    image: str = Field(..., description="Docker image for the agent container")
    templates: Optional[Dict[str, str]] = Field(default_factory=dict)
    resources: Dict[str, Any] = Field(default_factory=lambda: {"cpu_request": 1, "memory_request": "1Gi"})


class SWEAgentParams(BaseModel):
    """Typed schema for parameters passed via workflow with: block."""

    model: Dict[str, Any]  # JSON-decoded model config
    max_iterations: int = 100
    sweagent_config: str = "anthropic"
    tools_parse_function: str = "function_calling"
    max_observation_length: int = 100000


class SWEAgent(BaseTask):
    """
    SWE-Agent task — creates an Argo rollout task for automated code repair.

    Instance data (instance_id, dataset, split, base_commit, docker_image)
    arrives as an Argo artifact from SWE-bench-fetch, mounted at
    /tmp/instance_data/. The bash script reads it at runtime.

    Model config and agent params are rendered into the script at create_task()
    time via Jinja2 templates.

    Usage:
        >>> task = AutoTask.from_repo("ix-hub/SWE-agent")
        >>> argo_task = task.create_task(model={...}, max_iterations=50)
    """

    config_class = SWEAgentConfig
    config: SWEAgentConfig

    def build_task(self, **kwargs: Any) -> Task:
        """
        Create an Argo rollout Task for SWE-Agent.

        Args (from workflow with: block):
            model: Model configuration dict (provider, model, base_url, api_key, ...).
                   Passed as JSON string by the WorkflowTranslator; decoded here.
            max_iterations: Maximum agent iterations (default 100).
            sweagent_config: SWE-agent config name (default "anthropic").
            tools_parse_function: Tool parse function type (default "function_calling").
            max_observation_length: Max observation length (default 100000).

        Artifact inputs (wired by WorkflowTranslator, not in kwargs):
            instance_data: Mounted at /tmp/instance_data/ by Argo.

        Returns:
            Hera Task with Container + SWE-ReX sidecar.
        """
        kwargs = self.decode_json_params(kwargs, "model")
        params = SWEAgentParams(**kwargs)

        # Flatten model fields for template rendering
        model = params.model

        main_script = self.render_template(
            "main",
            {
                # Model config (rendered into script at build time)
                "provider": model.get("provider", model.get("type", "openai")),
                "model": model["model"],
                "base_url": model["base_url"],
                "api_key": model["api_key"],
                "temperature": model.get("temperature", 0.0),
                "top_p": model.get("top_p"),
                "num_retries": model.get("num_retries", 3),
                "completion_kwargs": model.get("completion_kwargs", {}),
                "max_tokens": model.get("max_tokens"),
                # Agent params
                "max_iterations": params.max_iterations,
                "sweagent_config": params.sweagent_config,
                "tools_parse_function": params.tools_parse_function,
                "max_observation_length": params.max_observation_length,
            },
        )

        inputs = self.build_inputs() + [
            OSSArtifact(
                name="swe-preprocess",
                path="/tmp/shared/swe-preprocess/",
                key="<key-to-swe-preprocess-in-oss>",
                archive=TarArchiveStrategy(),
            ),
            OSSArtifact(
                name="swe-rex",
                path="/tmp/shared/swe-rex/",
                key="<key-to-swe-rex-in-oss>",
                archive=TarArchiveStrategy(),
            ),
        ]
        outputs = self.build_outputs()

        sidecars = []
        if self.config.templates and "swe_rex" in self.config.templates:
            sidecars.append(self._create_swerex_sidecar())

        container = Container(
            name="sweagent",
            image=self.config.image,
            command=["bash", "-c", main_script],
            inputs=inputs,
            outputs=outputs,
            env=[Env(name="OUTPUT_DIR", value="/tmp/output/")],
            sidecars=sidecars,
            volumes=[EmptyDirVolume(name="shared-volume", mount_path="/tmp/shared/")],
            volume_mounts=[VolumeMount(name="result-volume", mount_path="/tmp/output/")],
            resources=Resources(
                cpu_request=self.config.resources.get("cpu_request", 1),
                memory_request=self.config.resources.get("memory_request", "1Gi"),
            ),
        )

        return Task(name="sweagent-rollout", template=container)

    def _create_swerex_sidecar(self) -> UserContainer:
        """Create SWE-ReX sidecar — reads instance_data from artifact at runtime."""
        swerex_script = self.render_template("swe_rex", {})
        return UserContainer(
            name="swerex-remote",
            image="<swerex-docker-image>",
            command=["bash", "-c", swerex_script],
            volume_mounts=[
                VolumeMount(name="shared-volume", mount_path="/tmp/shared/", read_only=False),
            ],
            resources=Resources(cpu_request=1, memory_request="2Gi"),
        )
