"""
Base classes for environments in Interaxions framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Union, Literal, Type, TypeVar

import yaml

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.schemas.job import XJob

# TypeVar for generic return types
TEnvironmentConfig = TypeVar("TEnvironmentConfig", bound="BaseEnvironmentConfig")
TEnvironmentFactory = TypeVar("TEnvironmentFactory", bound="BaseEnvironmentFactory")


class BaseEnvironment(BaseModel, ABC):
    """
    Base class for environment instances.
    
    An environment instance represents a specific task/problem with concrete data
    (e.g., a specific SWE-Bench problem like django__django-12345).
    Created by EnvironmentFactory.get_from_hf() or EnvironmentFactory.get_from_oss().
    """

    environment_id: str = Field(..., description="Unique environment/instance identifier")

    @abstractmethod
    def create_task(self, job: "XJob", **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow task for evaluating this environment instance.
        
        The environment extracts necessary information from the XJob protocol,
        including environment-specific parameters, runtime settings, etc.

        Args:
            job: XJob protocol containing all configuration and runtime information.
                 The environment will extract:
                 - job.environment.params: Environment-specific parameters
                 - job.runtime: Kubernetes/Argo runtime settings
            **kwargs: Additional implementation-specific parameters for extensibility.

        Returns:
            Hera Task object ready for use in a workflow.
            
        Example:
            >>> from interaxions.schemas import XJob, ...
            >>> job = XJob(...)
            >>> env = factory.get_from_hf(...)
            >>> task = env.create_task(job)
            
        Note:
            Concrete implementations can be more specific about what they need from XJob:
            
            def create_task(self, job: XJob, **kwargs: Any) -> Task:
                # Extract environment params
                predictions_path = job.environment.params.get('predictions_path', 'gold')
                
                # Auto-generate name from job
                name = f"env-{job.environment.environment_id}"
                
                # Create task...
        """
        pass


class BaseEnvironmentConfig(BaseModel):
    """
    Base configuration class for environments.
    
    This is the configuration loaded from config.yaml.
    Only contains the minimal required field that all environments need.
    """

    repo_type: Literal["environment"] = Field(default="environment", description="Repository type identifier")
    type: str = Field(..., description="Environment type")
    templates: Dict[str, str] = Field(default_factory=dict, description="Jinja2 templates for evaluation/execution")

    @classmethod
    def _load_config_dict(cls, repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load and parse config file from the environment directory.
        
        Args:
            repo_name_or_path: Repository name or path to the environment directory.
            
        Returns:
            Configuration dictionary.
        """
        # Find config file
        config_file = Path(repo_name_or_path) / "config.yaml"
        if not config_file.exists():
            config_file = Path(repo_name_or_path) / "config.yml"

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found in {repo_name_or_path}. "
                                    "Expected 'config.yaml' or 'config.yml'.")

        # Load and parse YAML
        with open(config_file, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        if not isinstance(config_dict, dict):
            raise ValueError(f"Invalid config file: {config_file}. Expected a dictionary.")

        return config_dict

    @classmethod
    def _load_templates(cls, config_dict: Dict[str, Any], repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load template files referenced in config.
        
        All templates must be file paths (e.g., "templates/evaluation.j2").
        Template files must exist in the environment directory.
        
        Args:
            config_dict: Configuration dictionary.
            repo_name_or_path: Repository name or path to the environment directory.
            
        Returns:
            Updated config_dict with templates loaded as strings.
            
        Raises:
            FileNotFoundError: If template file does not exist.
            ValueError: If template value is not a string.
        """
        if "templates" not in config_dict or not isinstance(config_dict["templates"], dict):
            return config_dict

        loaded_templates = {}
        for template_name, template_path in config_dict["templates"].items():
            if not isinstance(template_path, str):
                raise ValueError(f"Template '{template_name}' must be a file path string, "
                                 f"got {type(template_path).__name__}")

            # Resolve template file path
            template_file = Path(repo_name_or_path) / template_path

            if not template_file.exists():
                raise FileNotFoundError(f"Template file not found: {template_file}\n"
                                        f"Template '{template_name}' references '{template_path}' which does not exist.")

            # Load template content from file
            with open(template_file, "r", encoding="utf-8") as f:
                loaded_templates[template_name] = f.read()

        config_dict["templates"] = loaded_templates
        return config_dict

    @classmethod
    def from_repo(cls: Type[TEnvironmentConfig], repo_name_or_path: Union[str, Path]) -> TEnvironmentConfig:
        """
        Load environment configuration from repository.
        
        Args:
            repo_name_or_path: Repository name (e.g., "username/repo") or path to the directory 
                              containing config.yaml.
        
        Returns:
            Config instance.
        """
        repo_name_or_path = Path(repo_name_or_path)

        if not repo_name_or_path.exists():
            raise FileNotFoundError(f"Directory not found: {repo_name_or_path}")

        if not repo_name_or_path.is_dir():
            raise ValueError(f"Path must be a directory: {repo_name_or_path}")

        config_dict = cls._load_config_dict(repo_name_or_path)

        # Load templates from config
        config_dict = cls._load_templates(config_dict, repo_name_or_path)

        return cls(**config_dict)


class BaseEnvironmentFactory(ABC):
    """
    Base environment factory class (configuration manager + factory).
    
    This class manages environment configuration and creates environment instances.
    Use from_repo() to load configuration, then use get_from_hf()/get_from_oss()
    to create specific environment instances.
    
    The factory pattern is used because:
    1. Configuration (templates) is shared across instances
    2. Loading config once allows creating multiple instances efficiently
    3. Clear separation: Factory manages config, Environment is the actual instance
    """
    config_class: Type[BaseEnvironmentConfig] = BaseEnvironmentConfig
    config: BaseEnvironmentConfig

    def __init__(self, config: BaseEnvironmentConfig):
        """
        Initialize environment factory with configuration.
        
        Args:
            config: Environment configuration.
        """
        self.config = config

    @classmethod
    def from_repo(cls: Type[TEnvironmentFactory], repo_name_or_path: Union[str, Path]) -> TEnvironmentFactory:
        """
        Load environment configuration from repository.
        
        This creates a factory object that can be used to create multiple
        environment instances with get_from_hf() or get_from_oss().
        
        Args:
            repo_name_or_path: Repository name (e.g., "username/repo") or path to environment 
                              configuration directory.
            
        Returns:
            Environment factory object.
            
        Example:
            >>> # Load environment factory (configuration + templates)
            >>> factory = SWEBenchFactory.from_repo("ix-hub/swe-bench")
            >>> 
            >>> # Create multiple environment instances from the same config
            >>> env1 = factory.get_from_hf(environment_id="django__django-12345", ...)
            >>> env2 = factory.get_from_hf(environment_id="flask__flask-1234", ...)
            >>> 
            >>> # Create tasks for each environment (simplified API)
            >>> task1 = env1.create_task(predictions_path="/workspace/predictions.json")
            >>> task2 = env2.create_task(predictions_path="/workspace/predictions.json")
        """
        config = cls.config_class.from_repo(repo_name_or_path)
        return cls(config=config)

    @abstractmethod
    def get_from_hf(self, environment_id: str, **kwargs: Any) -> BaseEnvironment:
        """
        Get an environment instance from HuggingFace datasets.
        
        This is an abstract method that must be implemented by all concrete
        environment factories.
        
        Args:
            environment_id: Unique identifier for the environment instance.
            **kwargs: Additional parameters (dataset, split, etc.)
                     Each implementation defines its own required parameters.
        
        Returns:
            Environment instance.
        """
        pass

    @abstractmethod
    def get_from_oss(self, environment_id: str, **kwargs: Any) -> BaseEnvironment:
        """
        Get an environment instance from OSS (Object Storage Service).
        
        This is an abstract method that must be implemented by all concrete
        environment factories.
        
        Args:
            environment_id: Unique identifier for the environment instance.
            **kwargs: Additional parameters (bucket, key, region, etc.)
                     Each implementation defines its own required parameters.
        
        Returns:
            Environment instance.
        """
        pass
