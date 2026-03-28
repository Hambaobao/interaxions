"""
SWE-bench-fetch task: fetches a SWE-bench instance from HuggingFace
and writes the instance data as a JSON artifact for downstream tasks.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import Field

from hera.workflows import Container, Resources, Task, Env

from interaxions.tasks.base_task import BaseTask, BaseTaskConfig


class SWEBenchFetchConfig(BaseTaskConfig):
    """Configuration for SWE-bench-fetch, loaded from config.yaml."""

    type: Literal["swe-bench-fetch"] = Field(default="swe-bench-fetch")
    image: str = Field(..., description="Docker image containing the fetch script")
    templates: Optional[Dict[str, str]] = Field(default_factory=dict)


class SWEBenchFetch(BaseTask):
    """
    Fetches a SWE-bench instance from HuggingFace and writes instance data
    to an Argo artifact for downstream tasks (SWE-agent, SWE-bench-verify).

    The output artifact (instance_data) is a JSON file at /tmp/output/data.json
    containing: instance_id, dataset, split, problem_statement, base_commit,
    docker_image, workdir, language.

    Usage:
        >>> task = AutoTask.from_repo("ix-hub/SWE-bench-fetch")
        >>> argo_task = task.create_task(
        ...     instance_id="django__django-12345",
        ...     dataset="princeton-nlp/SWE-bench_Verified",
        ... )
    """

    config_class = SWEBenchFetchConfig
    config: SWEBenchFetchConfig

    def create_task(self, **kwargs: Any) -> Task:
        """
        Create an Argo task that fetches instance data from HuggingFace.

        Args (from workflow with: block):
            instance_id: SWE-bench instance identifier.
            dataset: HuggingFace dataset name (default from config.yaml).
            split: Dataset split (default from config.yaml).
            revision: Dataset revision (default from config.yaml).

        Returns:
            Hera Task whose output artifact contains the instance data JSON.
        """
        script = self.render_template("main", {
            "instance_id": kwargs.get("instance_id", ""),
            "dataset": kwargs.get("dataset", "princeton-nlp/SWE-bench_Verified"),
            "split": kwargs.get("split", "test"),
            "revision": kwargs.get("revision", ""),
        })

        outputs = self.build_outputs()

        container = Container(
            name="swe-bench-fetch",
            image=self.config.image,
            command=["bash", "-c", script],
            outputs=outputs,
            resources=Resources(cpu_request=1, memory_request="2Gi"),
            env=[Env(name="HF_HUB_ENABLE_HF_TRANSFER", value="1")],
        )

        return Task(name="swe-bench-fetch", template=container)
