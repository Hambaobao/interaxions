"""
Base class for generic tasks in the Interaxions framework.
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Literal, Type, TypeVar

from pydantic import Field

from interaxions.base import BaseRepo, BaseRepoConfig
from interaxions.schemas.task import TaskInputs, TaskOutputs  # re-imported for convenience

if TYPE_CHECKING:
    from hera.workflows import Task

TBaseTask = TypeVar("TBaseTask", bound="BaseTask")


class BaseTaskConfig(BaseRepoConfig):
    """
    Base configuration for tasks, loaded from config.yaml.

    The inputs/outputs fields declare the Argo-level interface of this task.
    They are used by WorkflowTranslator to wire artifact/parameter passing
    between tasks, and by the Hub index for UI display.
    """

    repo_type: Literal["task"] = Field(default="task")
    inputs: TaskInputs = Field(default_factory=TaskInputs)
    outputs: TaskOutputs = Field(default_factory=TaskOutputs)


class BaseTask(BaseRepo):
    """
    Base class for Argo task executors.

    A task repo must implement a class inheriting from BaseTask in its ix.py
    and define create_task() to return a Hera Task object.

    The task's Argo-level interface (parameters/artifacts it consumes and
    produces) is declared in config.yaml under inputs/outputs. The
    WorkflowTranslator uses these declarations to wire tasks together in a DAG
    automatically — the task author does not need to handle cross-task data
    passing manually.

    Example ix.py:

        class SWEAgent(BaseTask):
            config_class = SWEAgentConfig
            config: SWEAgentConfig

            def create_task(self, model: dict, max_iterations: int = 100, **kwargs) -> Task:
                container = Container(
                    name="sweagent",
                    image=self.config.image,
                    inputs=[Artifact(name=a.name, path=a.path)
                            for a in self.config.inputs.artifacts],
                    outputs=[Artifact(name=a.name, path=a.path)
                             for a in self.config.outputs.artifacts],
                )
                return Task(name="sweagent", template=container)
    """

    config_class: Type[BaseTaskConfig] = BaseTaskConfig
    config: BaseTaskConfig

    @abstractmethod
    def create_task(self, **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow Task.

        Receives resolved parameter values from the workflow's with: block.
        Artifact inputs/outputs declared in config.yaml are wired automatically
        by the WorkflowTranslator.

        Returns:
            Hera Task ready for use in a workflow DAG.
        """
        pass


# Re-export for backward compatibility with task repo ix.py files
from interaxions.schemas.task import (  # noqa: E402, F401
    TaskArtifact,
    TaskParameter,
    TaskInputs,
    TaskOutputs,
    Resources,
)
