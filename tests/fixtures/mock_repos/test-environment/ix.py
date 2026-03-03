"""
Mock environment for testing.
"""

from typing import TYPE_CHECKING, Any

from interaxions.environments.base_environment import BaseEnvironment, BaseEnvironmentConfig
from interaxions.schemas.task import Environment

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.schemas.job import XJob


class TestEnvironmentConfig(BaseEnvironmentConfig):
    """Configuration for test environment."""
    type: str = "test-environment"


class TestEnvironment(BaseEnvironment):
    """A minimal test environment for testing AutoEnvironment loading."""

    config_class = TestEnvironmentConfig
    config: TestEnvironmentConfig

    def get(self, id: str) -> Environment:
        """Return a stub Environment object with the given id."""
        return Environment(
            id=id,
            type=self.config.type,
            data={
                "instance_id": id,
                "problem_statement": f"Test problem for {id}",
                "repo": "test/repo",
                "base_commit": "abc123",
            },
        )

    def create_task(self, job: "XJob", environment: Environment, **kwargs: Any) -> "Task":
        """Create a stub test task (not a real Argo task)."""
        raise NotImplementedError("TestEnvironment.create_task is a stub for testing")

