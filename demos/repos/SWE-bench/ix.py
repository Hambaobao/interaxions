"""
SWE-Bench environment implementation.

Entry file for the Agent-Hub SWE-Bench environment repository.
Implements BaseEnvironment with:
  - get(id)          → fetch instance data from HuggingFace, return Environment
  - create_task(...) → create Argo verify Task using the Environment data object

"""

from typing import Any, Dict, Literal, Optional

from pydantic import Field

from hera.workflows import (
    Container,
    UserContainer,
    Artifact,
    Task,
    Env,
    Resources,
)
from hera.workflows.models import SecurityContext
from jinja2 import Template

from interaxions.schemas import XJob
from interaxions.schemas.task import Environment
from interaxions.environments.base_environment import BaseEnvironment, BaseEnvironmentConfig


class SWEBenchConfig(BaseEnvironmentConfig):
    """Configuration for SWE-Bench, loaded from config.yaml."""

    type: Literal["swe-bench"] = "swe-bench"

    # Default dataset/split — can be set in config.yaml or overridden via EnvironmentConfig.params
    dataset: str = Field(default="princeton-nlp/SWE-bench_Verified", description="HuggingFace dataset name")
    split: str = Field(default="test", description="Dataset split")
    revision: Optional[str] = Field(default=None, description="OSS dataset revision; if set, version passed to ossdata is 'split@revision'")

    images: Dict[str, str] = Field(
        default={"swe-bench": ""},
        description="Docker images used by this environment",
    )
    templates: Dict[str, str] = Field(
        default={"verify": ""},
        description="Jinja2 template strings (loaded from template files by from_repo)",
    )


class SWEBench(BaseEnvironment):
    """
    SWE-Bench environment — loads instance data and creates Argo verify tasks.

    Usage:
        >>> env_task = SWEBench.from_repo("Agent-Hub/SWE-Bench")
        >>> env = env_task.get("django__django-12345")
        >>> env.data["problem_statement"]

        >>> verify_task = env_task.create_task(job, environment=env)
    """

    config_class = SWEBenchConfig
    config: SWEBenchConfig

    def get(self, id: str, dataset: Optional[str] = None, split: Optional[str] = None, revision: Optional[str] = None, **kwargs) -> Environment:
        """
        Fetch SWE-Bench instance data from HuggingFace via datasets.

        Args:
            id: SWE-Bench instance identifier, e.g. "django__django-12345"
            dataset: Dataset name override. Falls back to config.yaml value if not provided.
            split: Dataset split override (e.g. "test", "dev").
                   Falls back to config.yaml value if not provided.
            revision: HuggingFace dataset revision override (e.g. "20260301").
                      Falls back to config.yaml value if not provided.
            **kwargs: Ignored; accepted for interface compatibility.

        Returns:
            Environment(id, type="swe-bench", data={...}) with fields:
              dataset, split, language, problem_statement,
              working_dir, base_commit, docker_image
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError("datasets is required. Install with: pip install datasets")

        dataset = dataset if dataset is not None else self.config.dataset
        split = split if split is not None else self.config.split
        revision = revision if revision is not None else self.config.revision

        item = load_dataset(
            name=dataset,
            split=split,
            revision=revision,
        ).filter(lambda x: x["instance_id"] == id)

        return Environment(
            id=id,
            type="swe-bench",
            data={
                "dataset": dataset,
                "split": split,
                "revision": revision,
                "language": item.get("language", "python"),
                "problem_statement": item.get("problem_statement", ""),
                "working_dir": item.get("workdir", "/testbed"),
                "base_commit": item["base_commit"],
                "docker_image": item["docker_image"],
            },
        )

    def create_task(self, job: XJob, environment: Environment, **kwargs: Any) -> Task:
        """
        Create an Argo verify Task for this SWE-Bench instance.

        Args:
            job: XJob with runtime config and workflow params.
            environment: Environment data returned by get().
                         Uses: id, data["dataset"], data["split"]
            **kwargs: Unused.

        Workflow params read (from job.workflow.params["environment"]["params"]):
            predictions_path: Path to the agent's output predictions file.
                              Default: "gold"

        Returns:
            Hera Task for Argo Workflows.
        """
        env_params = job.workflow.params.get("environment", {}).get("params", {})
        predictions_path = env_params.get("predictions_path", "gold")

        verify_template = Template(self.config.templates["verify"])
        verify_script = verify_template.render(
            dataset=environment.data["dataset"],
            split=environment.data["split"],
            instance_id=environment.id,
            predictions_path=predictions_path,
            output_dir="/tmp/output/",
        )

        inputs = [Artifact(name="result", path="/tmp/output/")]
        outputs = [Artifact(name="result", path="/tmp/output/")]
        sidecars = [self._create_dind_sidecar()]

        container = Container(
            name="swe-bench",
            labels={"job-id": job.job_id},
            image=self.config.images["swe-bench"],
            image_pull_policy=job.runtime.image_pull_policy,
            command=["/bin/bash", "-c", verify_script],
            inputs=inputs,
            outputs=outputs,
            env=[
                Env(name="DOCKER_HOST", value="tcp://localhost:2375"),
            ],
            resources=Resources(cpu_request=2, memory_request="8Gi"),
            sidecars=sidecars,
        )

        return Task(name="swe-bench", template=container)

    def _create_dind_sidecar(self) -> UserContainer:
        """
        Create a Docker-in-Docker sidecar for running SWE-bench containers.
        """
        return UserContainer(
            name="docker-daemon",
            image="<your-image-used-for-swe-bench>",
            security_context=SecurityContext(privileged=True),
            env=[Env(name="DOCKER_TLS_CERTDIR", value="")],
            command=["dockerd-entrypoint.sh"],
            args=["--tls=false", "--host=tcp://0.0.0.0:2375"],
            resources=Resources(cpu_request=3, memory_request="4Gi"),
        )
