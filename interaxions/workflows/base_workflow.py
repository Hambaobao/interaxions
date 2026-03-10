"""
Base classes for workflows in Interaxions framework.
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Type, TypeVar

from pydantic import Field

from interaxions.base import BaseRepo, BaseRepoConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import XJob

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

    Workflows orchestrate agents and environments into complete Argo Workflows.

    Inherited from BaseRepoObject:
        from_repo(repo_name_or_path)   – load config and instantiate
        render_template(name, context) – render a Jinja2 template from config

    Example:
        >>> workflow_template = AutoWorkflow.from_repo("swe-bench-workflow")
        >>> argo_workflow = workflow_template.create_workflow(job)
        >>> argo_workflow.create()
    """

    config_class: Type[BaseWorkflowConfig] = BaseWorkflowConfig
    config: BaseWorkflowConfig

    @abstractmethod
    def create_workflow(self, job: "XJob", **kwargs: Any) -> "Workflow":
        """
        Create an Argo Workflow from an XJob specification.

        The workflow orchestrates the entire execution by:
        1. Loading agent and environment from job specifications
        2. Creating agent and environment tasks by passing the job to them
        3. Defining task dependencies and workflow structure

        This method serves as the entry point for executing a complete job.

        Args:
            job: XJob protocol containing all configuration and runtime information.
                 The workflow will:
                 - Load scaffold from job.scaffold (repo_name_or_path, revision)
                 - Load environment from job.environment (repo_name_or_path, revision, source)
                 - Pass job to scaffold.create_task(job) and env.create_task(job)
                 - Use job.runtime for Kubernetes/Argo settings
                 - Extract job.workflow.extra_params for workflow-specific parameters
            **kwargs: Additional implementation-specific parameters for extensibility.

        Returns:
            Hera Workflow object ready for submission to Argo.

        Example:
            >>> from interaxions.schemas import XJob
            >>> from interaxions.hub import AutoWorkflow
            >>>
            >>> job = XJob(...)
            >>> workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
            >>> workflow = workflow_template.create_workflow(job)
            >>> workflow.create()  # Submit to Argo

        Note:
            Concrete implementations typically follow this pattern:

            def create_workflow(self, job: XJob, **kwargs: Any) -> Workflow:
                from interaxions.hub import AutoScaffold, AutoEnvironment

                # 1. Load components from job
                scaffold = AutoScaffold.from_repo(job.scaffold.repo_name_or_path, job.scaffold.revision)
                env = AutoEnvironment.from_repo(job.environment.repo_name_or_path, job.environment.revision)

                # 2. Fetch environment instance data
                environment = env.get(job.environment.environment_id)

                # 3. Create tasks
                scaffold_task = scaffold.create_task(job, environment)
                env_task = env.create_task(job, environment)

                # 4. Build workflow
                with Workflow(name=f"workflow-{environment.id}", namespace=job.runtime.namespace) as w:
                    scaffold_task >> env_task

                return w
        """
        pass
