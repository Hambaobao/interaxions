"""
Base class for environments in Interaxions framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Type, TypeVar, Union

from pydantic import Field

from interaxions.base_config import BaseRepoConfig

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.schemas.job import XJob
    from interaxions.schemas.task import Environment

# TypeVar for generic return types
TBaseEnvironment = TypeVar("TBaseEnvironment", bound="BaseEnvironment")
TBaseEnvironmentConfig = TypeVar("TBaseEnvironmentConfig", bound="BaseEnvironmentConfig")


class BaseEnvironmentConfig(BaseRepoConfig):
    """
    Base configuration class for environments, loaded from config.yaml.

    Concrete environment configs should define their own fields
    (images, templates, dataset info, etc.) based on their specific needs.
    """

    repo_type: Literal["environment"] = Field(default="environment", description="Repository type identifier")
    type: str = Field(..., description="Environment type (e.g., 'swe-bench')")


class BaseEnvironment(ABC):
    """
    Base class for all environment task executors.

    An environment repo must implement a class inheriting from BaseEnvironment
    in its ix.py entry file. It is responsible for:
    1. Fetching environment instance data by id (get)
    2. Creating an Argo Workflow Task for evaluation (create_task)

    Credentials and data source routing (HF token, OSS keys, etc.) are read
    from environment variables by the implementer — not passed as parameters.

    Example ix.py structure:
        class SWEBenchEnvironment(BaseEnvironment):
            config_class = SWEBenchConfig
            config: SWEBenchConfig

            def get(self, id: str, **kwargs) -> Environment:
                token = os.environ.get("HF_TOKEN")
                row = load_from_hf(id, self.config.dataset, token=token)
                return Environment(id=id, type="swe-bench", data=dict(row))

            def create_task(self, job: XJob, **kwargs) -> Task:
                ...
    """

    config_class: Type[BaseEnvironmentConfig] = BaseEnvironmentConfig
    config: BaseEnvironmentConfig

    def __init__(self, config: BaseEnvironmentConfig):
        self.config = config

    @classmethod
    def from_repo(cls: Type[TBaseEnvironment], repo_name_or_path: Union[str, Path]) -> TBaseEnvironment:
        """Load config from repo and instantiate."""
        config = cls.config_class.from_repo(repo_name_or_path)
        return cls(config=config)

    @abstractmethod
    def get(self, id: str, **kwargs: Any) -> "Environment":
        """
        Fetch environment instance data by id and return an Environment object.

        Credentials and data source (HF, OSS, etc.) are determined by the
        implementer, typically via environment variables.

        kwargs allows subclasses to accept optional runtime overrides (e.g.
        split, revision) that take precedence over config.yaml defaults.

        Args:
            id: Environment instance identifier (e.g., "django__django-12345")
            **kwargs: Optional runtime overrides passed by the workflow
                      (e.g. split="test", revision="20260301").

        Returns:
            Environment(id, type, data) containing all instance-specific data.

        Example:
            >>> env_task = AutoEnvironment.from_repo("ix-hub/swe-bench")
            >>> env: Environment = env_task.get("django__django-12345")
            >>> env.data["problem_statement"]
        """
        pass

    @abstractmethod
    def create_task(self, job: "XJob", environment: "Environment", **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow Task for evaluating this environment instance.

        The environment data is passed explicitly (returned by get()) so the
        task creator has access to all instance-specific information without
        making another remote call.

        Args:
            job: XJob containing runtime config and workflow params.
            environment: Environment instance data returned by get().
                         Contains id, type, and data dict with instance-specific fields.
            **kwargs: Additional implementation-specific parameters.

        Returns:
            Hera Task object ready for use in a workflow.
        """
        pass
