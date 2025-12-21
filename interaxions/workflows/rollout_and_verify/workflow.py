"""
Agent rollout and verification workflow implementation.

This workflow orchestrates an agent rollout and environment verification for general tasks.
"""

from typing import TYPE_CHECKING, Any, Literal

from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.agents.base_agent import BaseAgent
    from interaxions.environments.base_environment import BaseEnvironment


class RolloutAndVerifyConfig(BaseWorkflowConfig):
    """
    Configuration for Rollout and Verify Workflow.
    """

    type: Literal["rollout-and-verify"] = "rollout-and-verify"


class RolloutAndVerify(BaseWorkflow):
    """
    Generic rollout and verify workflow for orchestrating agent and environment tasks.
    
    This workflow runs agent rollout followed by environment verification.
    
    Example:
        >>> from interaxions import AutoAgent, AutoEnvironmentFactory, AutoWorkflow
        >>> 
        >>> # Load components
        >>> agent = AutoAgent.from_repo("swe-agent")
        >>> env_factory = AutoEnvironmentFactory.from_repo("swe-bench")
        >>> workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        >>> 
        >>> # Get environment instance
        >>> env = env_factory.get_from_hf(
        ...     environment_id="django__django-12345",
        ...     dataset="princeton-nlp/SWE-bench",
        ...     split="test"
        ... )
        >>> 
        >>> # Create workflow
        >>> workflow = workflow_template.create_workflow(
        ...     name="rollout-001",
        ...     agent=agent,
        ...     environment=env,
        ...     namespace="default",
        ... )
        >>> 
        >>> # Submit to Argo
        >>> workflow.create()
    """

    config_class = RolloutAndVerifyConfig
    config: RolloutAndVerifyConfig

    def create_workflow(
        self,
        name: str,
        *,
        agent: "BaseAgent",
        environment: "BaseEnvironment",
        namespace: str = "default",
        **kwargs: Any,
    ) -> "Workflow":
        """
        Create rollout and verify workflow with agent and environment tasks.
        
        Args:
            name: Workflow name.
            agent: Agent instance.
            environment: Environment instance.
            namespace: Kubernetes namespace (default: "default").
            **kwargs: Additional parameters passed to both agent and environment tasks.
            
        Returns:
            Hera Workflow object.
        """
        from hera.workflows import Workflow

        # Create agent task
        agent_task = agent.create_task(name="agent-rollout", **kwargs)

        # Create environment verification task
        env_task = environment.create_task(name="environment-verify", **kwargs)

        # Create workflow with task dependencies
        with Workflow(name=name, namespace=namespace) as w:
            # Define task order: agent rollout -> environment verify
            agent_task >> env_task

        return w
