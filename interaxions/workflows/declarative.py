"""
DeclarativeWorkflow: a workflow driven entirely by workflow.yaml.

AutoWorkflow.from_repo() loads this when a workflow.yaml file is present.
The WorkflowTranslator handles the translation to Hera.
"""

from pathlib import Path
from typing import Any, TYPE_CHECKING

from interaxions.schemas.workflow import WorkflowDefinition

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import Job


class DeclarativeWorkflow:
    """
    A workflow driven entirely by a declarative workflow.yaml file.

    No Python code is required in the repository — the WorkflowTranslator
    handles resolving inputs, loading tasks, and wiring Argo arguments.
    """

    def __init__(self, definition: WorkflowDefinition) -> None:
        self._definition = definition

    def create_workflow(self, job: "Job", **kwargs: Any) -> "Workflow":
        from interaxions.translator import WorkflowTranslator
        return WorkflowTranslator().translate(self._definition, job)

    @classmethod
    def from_repo(cls, repo_path: Path) -> "DeclarativeWorkflow":
        """Load a DeclarativeWorkflow from a repository containing workflow.yaml."""
        definition = WorkflowDefinition.from_yaml(repo_path / "workflow.yaml")
        return cls(definition)
