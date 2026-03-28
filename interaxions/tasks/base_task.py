"""
Base class for generic tasks in Interaxions framework.
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, List, Literal, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from interaxions.base import BaseRepo, BaseRepoConfig

if TYPE_CHECKING:
    from hera.workflows import Task

# TypeVar for generic return types
TBaseTask = TypeVar("TBaseTask", bound="BaseTask")


# ---------------------------------------------------------------------------
# Task interface declarations (for config.yaml and Hub index)
# ---------------------------------------------------------------------------


class TaskArtifact(BaseModel):
    """An artifact input or output for an Argo task."""

    name: str = Field(..., description="Artifact name used in Argo arguments")
    path: str = Field(..., description="Path inside the container where the artifact is mounted")
    description: Optional[str] = None


class TaskParameter(BaseModel):
    """A string parameter input or output for an Argo task."""

    name: str = Field(..., description="Parameter name")
    default: Optional[str] = Field(default=None, description="Default value if not provided")
    description: Optional[str] = None


class TaskInputs(BaseModel):
    """Declared inputs for a task (parameters + artifacts)."""

    parameters: List[TaskParameter] = Field(default_factory=list)
    artifacts: List[TaskArtifact] = Field(default_factory=list)


class TaskOutputs(BaseModel):
    """Declared outputs for a task (parameters + artifacts)."""

    parameters: List[TaskParameter] = Field(default_factory=list)
    artifacts: List[TaskArtifact] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Config base
# ---------------------------------------------------------------------------


class BaseTaskConfig(BaseRepoConfig):
    """
    Base configuration class for tasks, loaded from config.yaml.

    Concrete task configs should define their own fields
    (image, command, templates, etc.) based on their specific needs.

    The inputs/outputs fields declare the Argo-level interface of this task.
    They are used by:
    - The WorkflowTranslator to wire artifact/parameter passing between tasks
    - The platform Hub index for compatibility checking and UI display
    """

    repo_type: Literal["task"] = Field(default="task", description="Repository type identifier")
    inputs: TaskInputs = Field(default_factory=TaskInputs)
    outputs: TaskOutputs = Field(default_factory=TaskOutputs)


# ---------------------------------------------------------------------------
# Runtime base
# ---------------------------------------------------------------------------


class BaseTask(BaseRepo):
    """
    Base class for generic Argo task executors.

    A task repo must implement a class inheriting from BaseTask in its ix.py
    entry file and define create_task() to return a Hera Task object.

    The task's Argo-level interface (what parameters/artifacts it consumes
    and produces) is declared in config.yaml under inputs/outputs. This
    declaration is used by the WorkflowTranslator to automatically wire
    tasks together in a DAG — the task author does not need to handle
    cross-task data passing manually.

    Inherited from BaseRepo:
        from_repo(repo_name_or_path)   – load config and instantiate
        render_template(name, context) – render a Jinja2 template from config

    Example ix.py structure:
        class SWEAgent(BaseTask):
            config_class = SWEAgentConfig
            config: SWEAgentConfig

            def create_task(self, model: dict, max_iterations: int = 100, **kwargs) -> Task:
                script = self.render_template("main", {"model": model, ...})
                container = Container(
                    name="sweagent",
                    image=self.config.image,
                    command=["bash", "-c", script],
                    inputs=[
                        # Artifact paths declared in config.yaml inputs.artifacts
                        Artifact(name=a.name, path=a.path)
                        for a in self.config.inputs.artifacts
                    ],
                    outputs=[
                        Artifact(name=a.name, path=a.path)
                        for a in self.config.outputs.artifacts
                    ],
                )
                return Task(name="sweagent", template=container)

    Example usage:
        >>> task = AutoTask.from_repo("ix-hub/SWE-agent")
        >>> argo_task = task.create_task(model={"type": "litellm", ...}, max_iterations=50)
    """

    config_class: Type[BaseTaskConfig] = BaseTaskConfig
    config: BaseTaskConfig

    @abstractmethod
    def create_task(self, **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow Task.

        Receives resolved parameter values from the workflow's with: block.
        Artifact inputs/outputs declared in config.yaml are wired automatically
        by the WorkflowTranslator — do not expect artifact data as kwargs.

        Args:
            **kwargs: Parameter values passed from the workflow's with: block,
                      after ${{ inputs.xxx }} expressions have been resolved.

        Returns:
            Hera Task object ready for use in a workflow DAG.

        Example:
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
        pass
