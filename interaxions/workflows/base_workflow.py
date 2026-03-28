"""
Base classes for workflows in Interaxions framework.
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Type, TypeVar

from pydantic import Field

from interaxions.base import BaseRepo, BaseRepoConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import Job

# TypeVar for generic return types
TWorkflow = TypeVar("TWorkflow", bound="BaseWorkflow")


class BaseWorkflowConfig(BaseRepoConfig):
    """
    Base configuration class for workflows.

    This is a minimal base class. Concrete workflow configs should define
    their own fields based on their specific needs.
    """

    repo_type: Literal["workflow"] = Field(default="workflow", description="Repository type identifier")
    type: str = Field(..., description="Workflow type")


class BaseWorkflow(BaseRepo):
    """
    Base class for all workflows.

    A workflow orchestrates multiple tasks into a complete Argo Workflow DAG.
    Each workflow is a self-contained repository that defines which tasks to
    load, how to connect them, and how data flows between them via Argo
    parameters and artifacts.

    Inherited from BaseRepo:
        from_repo(repo_name_or_path)   – load config and instantiate
        render_template(name, context) – render a Jinja2 template from config

    Example:
        >>> workflow = AutoWorkflow.from_repo("ix-hub/swe-rollout-verify")
        >>> argo_workflow = workflow.create_workflow(job)
        >>> argo_workflow.create()  # submit to Argo
    """

    config_class: Type[BaseWorkflowConfig] = BaseWorkflowConfig
    config: BaseWorkflowConfig

    @abstractmethod
    def create_workflow(self, job: "Job", **kwargs: Any) -> "Workflow":
        """
        Create an Argo Workflow from a Job specification.

        The workflow composes AutoTask instances into a DAG, passing data
        between tasks via Argo parameters and artifacts.

        Args:
            job: Job containing workflow config (repo + params) and runtime settings.
                 All task configuration lives in job.workflow.params — the workflow
                 defines and validates what params it expects.
            **kwargs: Additional implementation-specific parameters.

        Returns:
            Hera Workflow object ready for submission to Argo.

        Example:
            def create_workflow(self, job: Job, **kwargs: Any) -> Workflow:
                from interaxions.hub import AutoTask

                fetch = AutoTask.from_repo(job.workflow.params["fetch_task"])
                agent = AutoTask.from_repo(job.workflow.params["agent_task"])
                eval  = AutoTask.from_repo(job.workflow.params["eval_task"])

                with Workflow(name=job.name, namespace=job.runtime.namespace) as w:
                    t1 = fetch.create_task(instance_id=job.workflow.params["instance_id"])
                    t2 = agent.create_task(model=job.workflow.params["model"])
                    t3 = eval.create_task()
                    t1 >> t2 >> t3

                return w
        """
        pass
