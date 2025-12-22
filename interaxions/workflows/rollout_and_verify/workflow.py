"""
Agent rollout and verification workflow implementation.

This workflow orchestrates an agent rollout and environment verification for general tasks.
"""

from typing import TYPE_CHECKING, Any, Literal, Optional

from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import Job


class RolloutAndVerifyConfig(BaseWorkflowConfig):
    """
    Configuration for Rollout and Verify Workflow.
    """

    type: Literal["rollout-and-verify"] = "rollout-and-verify"


class RolloutAndVerify(BaseWorkflow):
    """
    Generic rollout and verify workflow for orchestrating agent and environment tasks.
    
    This workflow runs agent rollout followed by environment verification.
    It serves as the entry point for executing a complete Job.
    
    Example:
        >>> from interaxions.schemas import Job, ScaffoldProto, EnvironmentProto, ...
        >>> from interaxions.hub import AutoWorkflow
        >>> 
        >>> # Define job
        >>> job = Job(
        ...     model=LiteLLMModel(...),
        ...     scaffold=ScaffoldProto(repo_name_or_path="swe-agent", params={...}),
        ...     environment=EnvironmentProto(
        ...         repo_name_or_path="swe-bench",
        ...         environment_id="django__django-12345",
        ...         source="hf",
        ...         source_params={"dataset": "princeton-nlp/SWE-bench", "split": "test"}
        ...     ),
        ...     workflow=WorkflowProto(repo_name_or_path="rollout-and-verify"),
        ...     runtime=RuntimeProto(namespace="default")
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

    def create_workflow(
        self,
        job: "Job",
        **kwargs: Any,
    ) -> "Workflow":
        """
        Create rollout and verify workflow from a Job specification.
        
        This is the entry point for executing a complete job. It:
        1. Loads agent and environment from job specifications
        2. Creates agent and environment tasks by passing the job to them
        3. Orchestrates the workflow with proper task dependencies
        
        Args:
            job: Job protocol containing all configuration and runtime information.
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
            >>> from interaxions.schemas import Job, ...
            >>> from interaxions.hub import AutoWorkflow
            >>> 
            >>> job = Job(...)
            >>> workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
            >>> workflow = workflow_template.create_workflow(job)
            >>> workflow.create()  # Submit to Argo
        """
        from hera.workflows import Workflow
        from interaxions.hub import AutoScaffold, AutoEnvironmentFactory

        # 1. Load agent scaffold from job
        scaffold = AutoScaffold.from_repo(
            job.scaffold.repo_name_or_path,
            job.scaffold.revision,
        )

        # 2. Load environment factory and get environment instance
        env_factory = AutoEnvironmentFactory.from_repo(
            job.environment.repo_name_or_path,
            job.environment.revision,
        )

        if job.environment.source == "hf":
            environment = env_factory.get_from_hf(
                environment_id=job.environment.environment_id,
                **job.environment.source_params,
            )
        elif job.environment.source == "oss":
            environment = env_factory.get_from_oss(
                environment_id=job.environment.environment_id,
                **job.environment.source_params,
            )
        else:
            raise ValueError(f"Unsupported environment source: {job.environment.source}")

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
