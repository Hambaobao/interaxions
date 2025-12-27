"""
Agent rollout and verification workflow implementation.

This workflow orchestrates an agent rollout and environment verification for general tasks.
"""

from typing import TYPE_CHECKING, Any, Literal, Optional, Dict

from pydantic import Field

from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import XJob


class RolloutAndVerifyConfig(BaseWorkflowConfig):
    """
    Configuration for Rollout and Verify Workflow.
    """
    type: Literal["rollout-and-verify"] = Field(default="rollout-and-verify", description="The type of the workflow config.")
    templates: Optional[Dict[str, str]] = Field(default=None, description="Jinja2 templates for script generation. Keys are template names, values are template strings.")


class RolloutAndVerify(BaseWorkflow):
    """
    Generic rollout and verify workflow for orchestrating agent and environment tasks.
    
    This workflow runs agent rollout followed by environment verification.
    It serves as the entry point for executing a complete XJob.
    
    Example:
        >>> from interaxions.schemas import XJob, Scaffold, Environment, Workflow, Runtime, ...
        >>> from interaxions.hub import AutoWorkflow
        >>> 
        >>> # Define job
        >>> job = XJob(
        ...     model=LiteLLMModel(...),
        ...     scaffold=Scaffold(repo_name_or_path="swe-agent", params={...}),
        ...     environment=Environment(
        ...         repo_name_or_path="swe-bench",
        ...         environment_id="django__django-12345",
        ...         source="hf",
        ...         params={"dataset": "princeton-nlp/SWE-bench", "split": "test"}
        ...     ),
        ...     workflow=Workflow(repo_name_or_path="rollout-and-verify"),
        ...     runtime=Runtime(namespace="default")
        ... )
        >>> 
        >>> # Load workflow template and execute job
        >>> workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        >>> workflow = workflow_template.create_workflow(job)
        >>> 
        >>> # Submit to Argo
        >>> workflow.create()
    """

    config_class = RolloutAndVerifyConfig
    config: RolloutAndVerifyConfig

    def create_workflow(self, job: "XJob", **kwargs: Any) -> "Workflow":
        """
        Create rollout and verify workflow from an XJob specification.
        
        This is the entry point for executing a complete job. It:
        1. Loads agent and environment from job specifications
        2. Creates agent and environment tasks by passing the job to them
        3. Orchestrates the workflow with proper task dependencies
        
        Args:
            job: XJob protocol containing all configuration and runtime information.
                 The workflow will:
                 - Load scaffold from job.scaffold (repo_name_or_path, revision)
                 - Load environment from job.environment (repo_name_or_path, revision, source)
                 - Pass job to scaffold.create_task(job) and env.create_task(job)
                 - Use job.runtime.namespace for Kubernetes namespace
                 - Use job.environment.environment_id for workflow naming
            **kwargs: Additional workflow-specific parameters for extensibility.
            
        Returns:
            Hera Workflow object ready for submission to Argo.
            
        Example:
            >>> from interaxions.schemas import XJob, ...
            >>> from interaxions.hub import AutoWorkflow
            >>> 
            >>> job = XJob(...)
            >>> workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
            >>> workflow = workflow_template.create_workflow(job)
            >>> workflow.create()  # Submit to Argo
        """
        from hera.workflows import Workflow
        from interaxions.hub import AutoScaffold, AutoEnvironment

        # 1. Load agent scaffold from job
        scaffold = AutoScaffold.from_repo(
            job.scaffold.repo_name_or_path,
            job.scaffold.revision,
            username=job.scaffold.username,
            token=job.scaffold.token,
        )

        # 2. Load environment instance (unified from_repo API)
        environment = AutoEnvironment.from_repo(
            repo_name_or_path=job.environment.repo_name_or_path,
            revision=job.environment.revision,
            environment_id=job.environment.environment_id,
            source=job.environment.source,
            username=job.environment.username,
            token=job.environment.token,
            **job.environment.params,
        )

        # 3. Auto-generate workflow name from job
        name = f"workflow-{scaffold.config.type}-{job.environment.environment_id}"

        # 4. Create tasks by passing job to them
        # Each component will extract what it needs from the job
        scaffold_task = scaffold.create_task(job)
        env_task = environment.create_task(job)

        # 5. Create workflow with task dependencies
        with Workflow(name=name, namespace=job.runtime.namespace) as w:
            # Define task order: scaffold rollout -> environment verify
            scaffold_task >> env_task

        return w
