"""
Base class for generic tasks in the Interaxions framework.
"""

import json
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, List, Literal, Type, TypeVar

from pydantic import Field

from interaxions.base import BaseRepo, BaseRepoConfig
from interaxions.schemas.task import TaskInputs, TaskOutputs  # re-imported for convenience

if TYPE_CHECKING:
    from hera.workflows import Artifact, Task

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

            def build_task(self, **kwargs) -> Task:
                kwargs = self.decode_json_params(kwargs, "model")
                container = Container(
                    name="sweagent",
                    image=self.config.image,
                    inputs=self.build_inputs(),
                    outputs=self.build_outputs(),
                )
                return Task(name="sweagent", template=container)
    """

    config_class: Type[BaseTaskConfig] = BaseTaskConfig
    config: BaseTaskConfig

    def build_inputs(self) -> List["Artifact"]:
        """Build Hera Artifact list from config.inputs.artifacts."""
        from hera.workflows import Artifact
        return [Artifact(name=a.name, path=a.path) for a in self.config.inputs.artifacts]

    def build_outputs(self) -> List["Artifact"]:
        """Build Hera Artifact list from config.outputs.artifacts."""
        from hera.workflows import Artifact
        return [Artifact(name=a.name, path=a.path) for a in self.config.outputs.artifacts]

    def decode_json_params(self, kwargs: dict, *keys: str) -> dict:
        """JSON-decode specified keys if they arrive as strings (WorkflowTranslator serialises dicts)."""
        result = dict(kwargs)
        for key in keys:
            if key in result and isinstance(result[key], str):
                result[key] = json.loads(result[key])
        return result

    def create_task(self, **kwargs: Any) -> "Task":
        """
        Validate params then delegate to build_task().

        Called by WorkflowTranslator. Do not override — implement build_task() instead.
        """
        self._validate_params(kwargs)
        return self.build_task(**kwargs)

    def _validate_params(self, kwargs: dict) -> None:
        """Check that all required parameters (no default in config.yaml) are present."""
        for param in self.config.inputs.parameters:
            if param.name not in kwargs and param.default is None:
                raise ValueError(
                    f"Task '{type(self).__name__}': required parameter "
                    f"'{param.name}' not provided."
                )

    @abstractmethod
    def build_task(self, **kwargs: Any) -> "Task":
        """
        Build and return a Hera Task.

        Implement this in your task class. Receives resolved parameter values
        from the workflow's with: block — required parameters are guaranteed
        to be present (validated by create_task before this is called).

        Artifact inputs/outputs declared in config.yaml are wired automatically
        by WorkflowTranslator; use build_inputs() / build_outputs() to get the
        corresponding Hera Artifact lists.

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
