"""
Base class for environments in Interaxions framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Type, TypeVar, Union

import yaml

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.schemas.job import XJob
    from interaxions.schemas.task import Environment

# TypeVar for generic return types
TBaseEnvironment = TypeVar("TBaseEnvironment", bound="BaseEnvironment")
TBaseEnvironmentConfig = TypeVar("TBaseEnvironmentConfig", bound="BaseEnvironmentConfig")


class BaseEnvironmentConfig(BaseModel):
    """
    Base configuration class for environments, loaded from config.yaml.

    Concrete environment configs should define their own fields
    (images, templates, dataset info, etc.) based on their specific needs.
    """

    repo_type: Literal["environment"] = Field(default="environment", description="Repository type identifier")
    type: str = Field(..., description="Environment type (e.g., 'swe-bench')")

    @classmethod
    def _load_config_dict(cls, repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        config_file = Path(repo_name_or_path) / "config.yaml"
        if not config_file.exists():
            config_file = Path(repo_name_or_path) / "config.yml"
        if not config_file.exists():
            raise FileNotFoundError(
                f"Config file not found in {repo_name_or_path}. "
                "Expected 'config.yaml' or 'config.yml'."
            )
        with open(config_file, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        if not isinstance(config_dict, dict):
            raise ValueError(f"Invalid config file: {config_file}. Expected a dictionary.")
        return config_dict

    @classmethod
    def _load_templates(cls, config_dict: Dict[str, Any], repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        if "templates" not in config_dict or not isinstance(config_dict["templates"], dict):
            return config_dict
        loaded_templates = {}
        for template_name, template_path in config_dict["templates"].items():
            if not isinstance(template_path, str):
                raise ValueError(
                    f"Template '{template_name}' must be a file path string, "
                    f"got {type(template_path).__name__}"
                )
            template_file = Path(repo_name_or_path) / template_path
            if not template_file.exists():
                raise FileNotFoundError(
                    f"Template file not found: {template_file}\n"
                    f"Template '{template_name}' references '{template_path}' which does not exist."
                )
            with open(template_file, "r", encoding="utf-8") as f:
                loaded_templates[template_name] = f.read()
        config_dict["templates"] = loaded_templates
        return config_dict

    @classmethod
    def from_repo(cls: Type[TBaseEnvironmentConfig], repo_name_or_path: Union[str, Path]) -> TBaseEnvironmentConfig:
        repo_name_or_path = Path(repo_name_or_path)
        if not repo_name_or_path.exists():
            raise FileNotFoundError(f"Directory not found: {repo_name_or_path}")
        if not repo_name_or_path.is_dir():
            raise ValueError(f"Path must be a directory: {repo_name_or_path}")
        config_dict = cls._load_config_dict(repo_name_or_path)
        config_dict = cls._load_templates(config_dict, repo_name_or_path)
        return cls(**config_dict)


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

            def get(self, id: str) -> Environment:
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
    def get(self, id: str) -> "Environment":
        """
        Fetch environment instance data by id and return an Environment object.

        Credentials and data source (HF, OSS, etc.) are determined by the
        implementer, typically via environment variables.

        Args:
            id: Environment instance identifier (e.g., "django__django-12345")

        Returns:
            Environment(id, type, data) containing all instance-specific data.

        Example:
            >>> env_task = AutoEnvironment.from_repo("ix-hub/swe-bench")
            >>> env: Environment = env_task.get("django__django-12345")
            >>> env.data["problem_statement"]
        """
        pass

    @abstractmethod
    def create_task(self, job: "XJob", **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow Task for evaluating this environment.

        Args:
            job: XJob containing runtime config and workflow params.
            **kwargs: Additional implementation-specific parameters.

        Returns:
            Hera Task object ready for use in a workflow.
        """
        pass
