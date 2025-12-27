"""
Mock scaffold for testing.
"""

from typing import Any, Dict

from hera.workflows import Task

from interaxions.scaffolds.base_scaffold import BaseScaffold, BaseScaffoldConfig


class TestScaffoldConfig(BaseScaffoldConfig):
    """Configuration for test scaffold."""
    type: str = "test-scaffold"
    test_param: str = "default_value"


class TestScaffold(BaseScaffold):
    """A minimal test scaffold."""

    config_class = TestScaffoldConfig

    def create_task(self, job: "XJob", **kwargs: Any) -> Task:
        """Create a test task."""
        from hera.workflows import Container

        return Task(
            name="test-task",
            container=Container(
                image="python:3.10",
                command=["echo", "test"],
            ),
        )
