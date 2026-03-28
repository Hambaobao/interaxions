"""
SWE rollout → verify workflow implementation.
"""

import os

from typing import Any, Dict, Literal

from hera.workflows import (
    Workflow,
    DAG,
    EmptyDirVolume,
    RetryStrategy,
    RetryPolicy,
)
from hera.workflows.models import TTLStrategy, Backoff, PodGC
from pydantic import BaseModel

from interaxions.hub import AutoScaffold, AutoEnvironment
from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig
from interaxions.schemas import XJob, ScaffoldConfig, EnvironmentConfig
from interaxions.schemas.task import Environment

# ── Workflow params schema ───────────────────────────────────────────────────


class SWERolloutVerifyParams(BaseModel):
    """
    Typed schema for job.workflow.params in this workflow.

    Workflows define their own params schema — XJob itself stays neutral.
    """

    scaffold: ScaffoldConfig = ScaffoldConfig(repo_name_or_path="")
    environment: EnvironmentConfig
    model: Dict[str, Any]  # raw dict; scaffold reads what it needs


# ── Workflow-specific typed environment ──────────────────────────────────────


class SWEEnvironment(Environment):
    """
    SWE-specific environment — extends Environment with per-instance config params.

    Inherits id, type, data from Environment (so downstream repos can still use
    environment.data["x"] unchanged), and adds fix_hack as a proper typed field
    sourced from EnvironmentConfig.params.
    """

    fix_hack: bool = False

    @classmethod
    def from_environment(cls, environment: Environment, env_config: EnvironmentConfig) -> "SWEEnvironment":
        """
        Build SWEEnvironment from raw Environment + EnvironmentConfig.

        Args:
            environment: Raw data object from env_task.get(id).
            env_config:  EnvironmentConfig carrying per-instance params (e.g. fix_hack).
        """
        return cls(
            id=environment.id,
            type=environment.type,
            data=environment.data,
            fix_hack=env_config.params.get("fix_hack", False),
        )


# ── Workflow config ──────────────────────────────────────────────────────────


class SWERolloutVerifyWorkflowConfig(BaseWorkflowConfig):
    """Configuration loaded from config.yaml."""

    type: Literal["swe-rollout-verify-workflow"] = "swe-rollout-verify-workflow"


# ── Workflow implementation ──────────────────────────────────────────────────


class SWERolloutVerifyWorkflow(BaseWorkflow):
    """
    Orchestrates: SWE-Agent rollout → SWE-Bench verify.

    Usage (from Agent-Hub or local path):
        >>> workflow = AutoWorkflow.from_repo("Agent-Hub/SWE-rollout-verify-workflow")
        >>> argo_wf = workflow.create_workflow(job)
        >>> argo_wf.create()
    """

    config_class = SWERolloutVerifyWorkflowConfig
    config: SWERolloutVerifyWorkflowConfig

    def create_workflow(self, job: XJob, **kwargs: Any) -> Workflow:
        """
        Build and return the full Argo Workflow for this job.

        Steps:
          1. Parse job.workflow.params → SWERolloutVerifyParams
          2. Load scaffold and environment executors via Auto classes
          3. Fetch environment instance data via env_task.get(id)
          4. Create all tasks, wire dependencies
          5. Return Argo Workflow object

        Args:
            job: XJob with workflow config and runtime settings.
            **kwargs: Passed through to scaffold/env create_task calls.

        Returns:
            Hera Workflow ready for .create() submission to Argo.
        """
        # 1. Parse and validate workflow-specific params
        params = SWERolloutVerifyParams(**job.workflow.params)

        # 2. Load executors
        scaffold = AutoScaffold.from_repo(
            repo_name_or_path=params.scaffold.repo_name_or_path,
            revision=params.scaffold.revision,
            username=params.scaffold.username or os.environ.get("AGENT_HUB_USERNAME"),
            token=params.scaffold.token or os.environ.get("AGENT_HUB_TOKEN"),
        )
        env_task = AutoEnvironment.from_repo(
            repo_name_or_path=params.environment.repo_name_or_path,
            revision=params.environment.revision,
            username=params.environment.username or os.environ.get("AGENT_HUB_USERNAME"),
            token=params.environment.token or os.environ.get("AGENT_HUB_TOKEN"),
        )

        # 3. Fetch environment instance data, then wrap in typed SWEEnvironment
        #    dataset/split/revision in EnvironmentConfig.params override config.yaml defaults.
        env: Environment = env_task.get(
            params.environment.id,
            dataset=params.environment.params.get("dataset"),
            split=params.environment.params.get("split"),
            revision=params.environment.params.get("revision"),
        )
        swe_env = SWEEnvironment.from_environment(env, params.environment)

        # 4. Build Argo Workflow
        with Workflow(
                api_version="argoproj.io/v1alpha1",
                namespace=job.runtime.namespace,
                generate_name="SWE-rollout-verify-",
                labels=job.labels,
                entrypoint="entrypoint",
                ttl_strategy=TTLStrategy(
                    seconds_after_success=60,
                    seconds_after_failure=60 * 30,
                ),
                dns_policy="ClusterFirst",
                volumes=[
                    EmptyDirVolume(name="result-volume"),
                ],
                retry_strategy=RetryStrategy(
                    backoff=Backoff(duration="1m", factor=2),
                    limit=3,
                    retry_policy=RetryPolicy.always,
                ),
                active_deadline_seconds=job.runtime.active_deadline_seconds,
                pod_gc=PodGC(strategy="OnWorkflowSuccess"),
        ) as w:

            with DAG(name="entrypoint"):

                rollout_task = scaffold.create_task(job, environment=swe_env, **kwargs)

                verify_task = env_task.create_task(job, environment=swe_env, **kwargs)
                verify_task.dependencies = [rollout_task.name]
                verify_task.arguments = [rollout_task.get_artifact("result")]

        return w
