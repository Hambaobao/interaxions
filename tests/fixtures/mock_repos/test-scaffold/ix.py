"""
Mock scaffold for testing.
"""

from typing import TYPE_CHECKING, Any

from interaxions.scaffolds.base_scaffold import BaseScaffold, BaseScaffoldConfig

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.schemas.job import XJob
    from interaxions.schemas.task import Environment


class TestScaffoldConfig(BaseScaffoldConfig):
    """Configuration for test scaffold."""
    type: str = "test-scaffold"
    test_param: str = "default_value"
    max_iterations: int = 5


class TestScaffold(BaseScaffold):
    """A minimal test scaffold for testing AutoScaffold loading."""

    config_class = TestScaffoldConfig
    config: TestScaffoldConfig

    def create_task(self, job: "XJob", environment: "Environment", **kwargs: Any) -> "Task":
        """Create a stub test task (not a real Argo task)."""
        raise NotImplementedError("TestScaffold.create_task is a stub for testing")

