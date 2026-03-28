"""
SWE-Agent scaffold implementation.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from hera.workflows import (
    Artifact,
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

from interaxions.scaffolds.base_scaffold import BaseScaffold, BaseScaffoldConfig
from interaxions.schemas import XJob
from interaxions.schemas.task import Environment


class SWEAgentConfig(BaseScaffoldConfig):
    """
    Configuration for SWE-Agent, loaded from config.yaml.

    Deployment-related and structural config only.
    Runtime parameters (max_iterations, etc.) come from job.workflow.params.scaffold.params.
    """

    type: Literal["swe-agent"] = Field(default="swe-agent", description="Scaffold type identifier")
    image: str = Field(..., description="Docker image to use for the agent container")
    templates: Optional[Dict[str, str]] = Field(
        default={
            "main": "",
            "swe_rex": ""
        },
        description="Jinja2 templates loaded from config.yaml template paths",
    )
    resources: Dict[str, Any] = Field(
        default_factory=lambda: {
            "cpu_request": 1,
            "memory_request": "1Gi"
        },
        description="Container resource requests",
    )


class SWEAgentContext(BaseModel):
    """Context for rendering SWE-Agent main script template (main.j2)."""

    # From environment
    instance_id: str
    dataset: str
    split: str
    working_dir: str
    base_commit: str
    docker_image: str

    # From model
    provider: str = Field(default="openai")
    model: str
    base_url: str
    api_key: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    num_retries: int = 3
    completion_kwargs: Dict[str, Any] = Field(default_factory=dict)

    # Agent runtime (from scaffold params)
    sweagent_config: str = "anthropic"
    tools_parse_function: str = "function_calling"
    max_iterations: int = 100
    max_observation_length: int = 100000


class SWEReXContext(BaseModel):
    """Context for rendering SWE-ReX sidecar script template (swe_rex.j2)."""

    instance_id: str
    dataset: str
    split: str
    docker_image: str
    fix_hack: bool = False


class SWEAgent(BaseScaffold):
    """
    SWE-Agent scaffold — creates Argo rollout tasks for automated code repair.

    Usage:
        >>> scaffold = SWEAgent.from_repo("Agent-Hub/SWE-Agent")
        >>> rollout_task = scaffold.create_task(job, environment=env)
    """

    config_class = SWEAgentConfig
    config: SWEAgentConfig

    def _build_context(self, job: XJob, environment: Environment) -> SWEAgentContext:
        """
        Build SWEAgentContext from job.workflow.params and environment.

        Args:
            job: XJob with model config in job.workflow.params["model"]
                 and scaffold params in job.workflow.params["scaffold"]["params"].
            environment: Typed SWEEnvironment (or any object with matching attributes).
        """
        model_data = job.workflow.params.get("model", {})
        scaffold_params = job.workflow.params.get("scaffold", {}).get("params", {})

        return SWEAgentContext(
            # From environment data
            instance_id=environment.id,
            dataset=environment.data["dataset"],
            split=environment.data["split"],
            working_dir=environment.data["working_dir"],
            base_commit=environment.data["base_commit"],
            docker_image=environment.data["docker_image"],
            # From model config
            provider=model_data.get("provider", model_data.get("type", "openai")),
            model=model_data["model"],
            base_url=model_data["base_url"],
            api_key=model_data["api_key"],
            temperature=model_data.get("temperature"),
            top_p=model_data.get("top_p"),
            num_retries=model_data.get("num_retries", 3),
            completion_kwargs=model_data.get("completion_kwargs", {}),
            # From scaffold params
            sweagent_config=scaffold_params.get("sweagent_config", "anthropic"),
            tools_parse_function=scaffold_params.get("tools_parse_function", "function_calling"),
            max_iterations=scaffold_params.get("max_iterations", 100),
            max_observation_length=scaffold_params.get("max_observation_length", 100000),
        )

    def create_task(self, job: XJob, environment: Environment, **kwargs: Any) -> Task:
        """
        Create an Argo rollout Task for SWE-Agent.

        Args:
            job: XJob with runtime config and workflow params.
                 Reads: job.workflow.params["model"], job.workflow.params["scaffold"]["params"]
            environment: Environment data from env_task.get(id).
                         Uses: id, data["dataset"], data["split"], data["working_dir"],
                               data["base_commit"], data["docker_image"]
            **kwargs: Unused.

        Returns:
            Hera Task with Container template.
        """
        context = self._build_context(job, environment)

        swerex_context = SWEReXContext(
            instance_id=context.instance_id,
            dataset=context.dataset,
            split=context.split,
            docker_image=context.docker_image,
            fix_hack=getattr(environment, "fix_hack", False),
        )

        inputs = [
            OSSArtifact(
                name="swe-preprocess",
                path="<path-to-swe-preprocess-in-container>",
                key="<key-to-swe-preprocess-in-oss>",
                archive=TarArchiveStrategy(),
            ),
            OSSArtifact(
                name="swe-rex",
                path="<path-to-swe-rex-in-container>",
                key="<key-to-swe-rex-in-oss>",
                archive=TarArchiveStrategy(),
            ),
        ]
        outputs = [
            Artifact(name="result", path="/tmp/output/"),
        ]

        main_script = self.render_template("main", context.model_dump())

        sidecars = []
        if self.config.templates and "swe_rex" in self.config.templates:
            sidecars.append(self._create_swerex_sidecar(job, swerex_context))

        container = Container(
            name="sweagent",
            labels={
                "job-id": job.job_id,
                "task-type": "rollout",
                "task-name": "sweagent",
            },
            image=self.config.image,
            image_pull_policy=job.runtime.image_pull_policy,
            command=["bash", "-c", main_script],
            inputs=inputs,
            outputs=outputs,
            env=[
                Env(name="OUTPUT_DIR", value="/tmp/output/"),
            ],
            sidecars=sidecars,
            volumes=[
                EmptyDirVolume(name="shared-volume", mount_path="/tmp/shared/"),
            ],
            volume_mounts=[
                VolumeMount(name="result-volume", mount_path="/tmp/output/"),
            ],
            resources=Resources(
                cpu_request=self.config.resources.get("cpu_request", 1),
                memory_request=self.config.resources.get("memory_request", "1Gi"),
            ),
        )

        return Task(name="sweagent-rollout", template=container)

    def _create_swerex_sidecar(self, job: XJob, context: SWEReXContext) -> UserContainer:
        """Create SWE-ReX sidecar container."""
        swerex_script = self.render_template("swe_rex", context.model_dump())

        return UserContainer(
            name="swerex-remote",
            image=context.docker_image,
            image_pull_policy=job.runtime.image_pull_policy,
            command=["bash", "-c", swerex_script],
            env=[
                # TODO: Add environment variables for SWE-Preprocess if needed
                # TODO: Add environment variables for SWE-ReX if needed
            ],
            volume_mounts=[
                VolumeMount(name="shared-volume", mount_path="/tmp/shared/", read_only=False),
            ],
            resources=Resources(cpu_request=1, memory_request="2Gi"),
        )
