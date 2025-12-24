"""
Test workflow implementation for testing.
"""

from typing import TYPE_CHECKING, Any, Literal, Optional, Dict

from pydantic import Field

from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig

if TYPE_CHECKING:
    from hera.workflows import Workflow
    from interaxions.schemas.job import Job


class TestWorkflowConfig(BaseWorkflowConfig):
    """Configuration for test workflow."""
    type: Literal["test-workflow"] = Field(default="test-workflow")
    templates: Optional[Dict[str, str]] = Field(default=None, description="Jinja2 templates")


class TestWorkflow(BaseWorkflow):
    """Test workflow for unit testing."""
    
    config_class = TestWorkflowConfig
    config: TestWorkflowConfig
    
    def create_workflow(self, job: "Job", **kwargs: Any) -> "Workflow":
        """Create test workflow."""
        raise NotImplementedError("Test workflow doesn't implement create_workflow")

