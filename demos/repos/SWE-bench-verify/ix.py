"""
SWE-bench-verify task: runs SWE-bench evaluation on agent results.
"""

from typing import Any, Literal, Optional

from pydantic import Field

from hera.workflows import (
    Container,
    UserContainer,
    Env,
    Resources,
    Task,
)
from hera.workflows.models import SecurityContext

from interaxions.tasks.base_task import BaseTask, BaseTaskConfig


class SWEBenchVerifyConfig(BaseTaskConfig):
    """Configuration for SWE-bench-verify, loaded from config.yaml."""

    type: Literal["swe-bench-verify"] = Field(default="swe-bench-verify")
    image: str = Field(..., description="Docker image for the evaluation container")
    templates: Optional[dict] = Field(default_factory=dict)


class SWEBenchVerify(BaseTask):
    """
    SWE-bench-verify task — evaluates agent predictions against SWE-bench.

    Receives the agent result artifact from SWE-agent, reads instance data
    embedded in it, and runs the SWE-bench evaluation harness.

    Usage:
        >>> task = AutoTask.from_repo("ix-hub/SWE-bench-verify")
        >>> argo_task = task.create_task(
        ...     predictions_path="/tmp/output/output.sweb.jsonl",
        ...     job_id="job-abc123",
        ... )
    """

    config_class = SWEBenchVerifyConfig
    config: SWEBenchVerifyConfig

    def create_task(self, **kwargs: Any) -> Task:
        """
        Create an Argo verify Task for SWE-bench evaluation.

        Args (from workflow with: block):
            predictions_path: Path to predictions file, or "gold" (default "gold").
            job_id: Job ID for metrics reporting.

        Artifact inputs (wired by WorkflowTranslator):
            result: Agent output artifact from SWE-agent, mounted at /tmp/output/.

        Returns:
            Hera Task with evaluation container + Docker-in-Docker sidecar.
        """
        predictions_path = kwargs.get("predictions_path", "gold")
        job_id = kwargs.get("job_id", "")

        verify_script = self.render_template(
            "verify",
            {"predictions_path": predictions_path, "job_id": job_id},
        )

        inputs = self.build_inputs()
        outputs = self.build_outputs()

        container = Container(
            name="swe-bench-verify",
            image=self.config.image,
            command=["/bin/bash", "-c", verify_script],
            inputs=inputs,
            outputs=outputs,
            env=[Env(name="DOCKER_HOST", value="tcp://localhost:2375")],
            resources=Resources(cpu_request=2, memory_request="8Gi"),
            sidecars=[self._create_dind_sidecar()],
        )

        return Task(name="swe-bench-verify", template=container)

    def _create_dind_sidecar(self) -> UserContainer:
        """Docker-in-Docker sidecar for running SWE-bench containers."""
        return UserContainer(
            name="docker-daemon",
            image="<your-image-used-for-swe-bench>",
            security_context=SecurityContext(privileged=True),
            env=[Env(name="DOCKER_TLS_CERTDIR", value="")],
            command=["dockerd-entrypoint.sh"],
            args=["--tls=false", "--host=tcp://0.0.0.0:2375"],
            resources=Resources(cpu_request=3, memory_request="4Gi"),
        )
