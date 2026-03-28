"""
DeclarativeWorkflow: a BaseWorkflow implementation driven by workflow.yaml.

When AutoWorkflow.from_repo() detects a workflow.yaml file in the repository,
it returns a DeclarativeWorkflow instead of requiring a BaseWorkflow subclass
in ix.py. The WorkflowTranslator handles the translation to Hera.
"""

from pathlib import Path
from typing import Any, TYPE_CHECKING

from interaxions.schemas.workflow_definition import WorkflowDefinition
from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import Job


class DeclarativeWorkflow(BaseWorkflow):
    """
    A workflow driven entirely by a declarative workflow.yaml file.

    No Python code is required in the repository — the WorkflowTranslator
    handles resolving inputs, loading tasks, and wiring Argo arguments.

    For complex workflows that need custom logic, use a BaseWorkflow subclass
    in ix.py instead (the Python escape hatch).
    """

    _definition: WorkflowDefinition

    def create_workflow(self, job: "Job", **kwargs: Any) -> "Workflow":
        from interaxions.translator import WorkflowTranslator
        return WorkflowTranslator().translate(self._definition, job)

    @classmethod
    def from_repo(cls, repo_path: Path) -> "DeclarativeWorkflow":
        """
        Load a DeclarativeWorkflow from a repository containing workflow.yaml.

        Args:
            repo_path: Path to the repository directory.

        Returns:
            DeclarativeWorkflow instance with the parsed definition attached.
        """
        definition = WorkflowDefinition.from_yaml(repo_path / "workflow.yaml")
        config = BaseWorkflowConfig(type=definition.type, repo_type="workflow")
        instance = cls(config=config)
        instance._definition = definition
        return instance
