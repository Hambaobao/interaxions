"""
Mock task for testing.
"""

from typing import TYPE_CHECKING, Any

from interaxions.tasks.base_task import BaseTask, BaseTaskConfig

if TYPE_CHECKING:
    from hera.workflows import Task


class TestTaskConfig(BaseTaskConfig):
    """Configuration for test task."""
    type: str = "test-task"
    image: str = "ghcr.io/ix-hub/test-task:latest"
    command: str = "python run.py"


class TestTask(BaseTask):
    """A minimal test task for testing AutoTask loading."""

    config_class = TestTaskConfig
    config: TestTaskConfig

    def create_task(self, **kwargs: Any) -> "Task":
        """Create a stub test task (not a real Argo task)."""
        raise NotImplementedError("TestTask.create_task is a stub for testing")

