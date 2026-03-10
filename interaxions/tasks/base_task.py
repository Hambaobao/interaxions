"""
Base class for generic tasks in Interaxions framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Type, TypeVar, Union

from pydantic import Field

from interaxions.base_config import BaseRepoConfig

if TYPE_CHECKING:
    from hera.workflows import Task

# TypeVar for generic return types
TBaseTaskConfig = TypeVar("TBaseTaskConfig", bound="BaseTaskConfig")
TBaseTask = TypeVar("TBaseTask", bound="BaseTask")


class BaseTaskConfig(BaseRepoConfig):
    """
    Base configuration class for tasks, loaded from config.yaml.

    Concrete task configs should define their own fields
    (image, command, templates, etc.) based on their specific needs.
    """

    repo_type: Literal["task"] = Field(default="task", description="Repository type identifier")


class BaseTask(ABC):
    """
    Base class for generic Argo task executors.

    Unlike BaseScaffold (agent runner) and BaseEnvironment (eval environment),
    BaseTask is not coupled to any specific job schema or environment schema.
    It is suitable for arbitrary Argo tasks such as data preprocessing, model
    training, result aggregation, notifications, and so on.

    A task repo must implement a class inheriting from BaseTask in its ix.py
    entry file and define create_task() to return a Hera Task object.

    Example ix.py structure:
        class DataPreprocessTask(BaseTask):
            config_class = DataPreprocessConfig
            config: DataPreprocessConfig

            def create_task(self, dataset: str, **kwargs) -> Task:
                container = Container(
                    name="preprocess",
                    image=self.config.image,
                    command=["python", "preprocess.py", "--dataset", dataset],
                )
                return Task(name="preprocess", template=container)

    Example usage:
        >>> task = AutoTask.from_repo("ix-hub/data-preprocess")
        >>> argo_task = task.create_task(dataset="my-dataset")

        >>> # Compose with AutoWorkflow freely — no XJob or Environment required
        >>> with Workflow(name="my-pipeline") as w:
        ...     t1 = task.create_task(dataset="swe-bench")
        ...     t2 = other_task.create_task()
        ...     t1 >> t2
    """

    config_class: Type[BaseTaskConfig] = BaseTaskConfig
    config: BaseTaskConfig

    def __init__(self, config: BaseTaskConfig):
        self.config = config

    @classmethod
    def from_repo(cls: Type[TBaseTask], repo_name_or_path: Union[str, Path]) -> TBaseTask:
        """Load config from repo and instantiate."""
        config = cls.config_class.from_repo(repo_name_or_path)
        return cls(config=config)

    @abstractmethod
    def create_task(self, **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow Task.

        Unlike BaseScaffold.create_task() and BaseEnvironment.create_task(),
        this method carries no assumptions about agent/environment coupling.
        All inputs are passed as free-form kwargs, defined entirely by the
        concrete implementation.

        Args:
            **kwargs: Implementation-specific parameters (e.g. dataset name,
                      model path, output bucket, etc.).

        Returns:
            Hera Task object ready for use in a workflow.

        Example:
            def create_task(self, dataset: str, output_path: str, **kwargs) -> Task:
                container = Container(
                    name="preprocess",
                    image=self.config.image,
                    command=["python", "run.py", "--dataset", dataset],
                )
                return Task(name="preprocess", template=container)
        """
        pass
