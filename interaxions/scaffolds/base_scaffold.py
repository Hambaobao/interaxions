"""
Base class for agent scaffolds in Interaxions framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Type, TypeVar, Union

from pydantic import Field
from jinja2 import Template

from interaxions.base_config import BaseRepoConfig

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.schemas.job import XJob
    from interaxions.schemas.task import Environment

# TypeVar for generic return types
TBaseScaffoldConfig = TypeVar("TBaseScaffoldConfig", bound="BaseScaffoldConfig")
TBaseScaffold = TypeVar("TBaseScaffold", bound="BaseScaffold")


class BaseScaffoldConfig(BaseRepoConfig):
    """
    Base configuration class for scaffolds, loaded from config.yaml.

    Concrete scaffold configs should define their own fields
    (image, templates, etc.) based on their specific needs.
    """

    repo_type: Literal["scaffold"] = Field(default="scaffold", description="Repository type identifier")


class BaseScaffold(ABC):
    """
    Base class for all scaffold task executors.

    A scaffold repo must implement a class inheriting from BaseScaffold
    in its ix.py entry file. It is responsible for creating an Argo Task
    that runs the agent against an environment.

    The environment data (fetched by BaseEnvironment.get()) is passed
    explicitly to create_task(), giving the scaffold access to instance-
    specific information (problem statement, base commit, docker image, etc.)
    without coupling it to the environment loading mechanism.

    Example ix.py structure:
        class SWEAgent(BaseScaffold):
            config_class = SWEAgentConfig
            config: SWEAgentConfig

            def create_task(self, job: XJob, environment: Environment, **kwargs) -> Task:
                script = self.render_template("main", {
                    "instance_id": environment.id,
                    "problem_statement": environment.data["problem_statement"],
                    ...
                })
                ...
    """

    config_class: Type[BaseScaffoldConfig] = BaseScaffoldConfig
    config: BaseScaffoldConfig

    def __init__(self, config: BaseScaffoldConfig):
        self.config = config

    @classmethod
    def from_repo(cls: Type[TBaseScaffold], repo_name_or_path: Union[str, Path]) -> TBaseScaffold:
        """Load config from repo and instantiate."""
        config = cls.config_class.from_repo(repo_name_or_path)
        return cls(config=config)

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with the given context.

        Templates are stored as strings in config.templates (loaded by from_repo).

        Args:
            template_name: Name of the template (e.g., "main", "sidecar").
            context: Dictionary of variables to pass to the template.

        Returns:
            Rendered template string.

        Raises:
            ValueError: If template not found in config.
        """
        if not hasattr(self.config, 'templates') or not self.config.templates:
            raise ValueError(f"No templates found in scaffold config. "
                             f"Scaffold must be loaded via from_repo() to use templates.")
        if template_name not in self.config.templates:
            available = list(self.config.templates.keys())
            raise ValueError(f"Template '{template_name}' not found in scaffold config. "
                             f"Available templates: {available}")
        template_str = self.config.templates[template_name]
        template = Template(template_str)
        return template.render(context)

    @abstractmethod
    def create_task(self, job: "XJob", environment: "Environment", **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow Task for running this scaffold against an environment.

        The environment data is passed explicitly so the scaffold has access to
        instance-specific information without coupling to the environment loading mechanism.

        Args:
            job: XJob containing runtime config and workflow params.
            environment: Environment instance data returned by BaseEnvironment.get().
                         Contains id, type, and data dict with instance-specific fields.
            **kwargs: Additional implementation-specific parameters.

        Returns:
            Hera Task object ready for use in a workflow.

        Example:
            def create_task(self, job: XJob, environment: Environment, **kwargs) -> Task:
                script = self.render_template("main", {
                    "instance_id": environment.id,
                    "problem_statement": environment.data["problem_statement"],
                    "model": job.workflow.params.get("model", {}),
                    **job.workflow.params.get("scaffold", {}).get("extra_params", {}),
                })
                container = Container(
                    name=f"agent-{environment.id}",
                    image=self.config.image,
                    command=["bash", "-c", script],
                    ...
                )
                return Task(name=f"agent-{environment.id}", template=container)
        """
        pass
