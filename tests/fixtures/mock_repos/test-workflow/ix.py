"""
Mock workflow for testing.
"""

from typing import TYPE_CHECKING, Any, Dict, Literal, Optional

from pydantic import Field

from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import XJob


class TestWorkflowConfig(BaseWorkflowConfig):
    """Configuration for test workflow."""
    type: Literal["test-workflow"] = Field(default="test-workflow")
    templates: Optional[Dict[str, str]] = Field(default=None, description="Jinja2 templates")


class TestWorkflow(BaseWorkflow):
    """Test workflow for unit/integration testing."""

    config_class = TestWorkflowConfig
    config: TestWorkflowConfig

    def create_workflow(self, job: "XJob", **kwargs: Any) -> "Workflow":
        """Create test workflow (stub — does not build a real Argo Workflow)."""
        raise NotImplementedError("TestWorkflow.create_workflow is a stub for testing")

