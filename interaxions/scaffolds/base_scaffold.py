"""
Base classes for agent scaffolds in Interaxions framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, Union, Literal, Type, TypeVar

import yaml

from pydantic import BaseModel, Field
from jinja2 import Template

if TYPE_CHECKING:
    from hera.workflows import Task
    from interaxions.schemas.job import XJob

# TypeVar for generic return types
TScaffoldConfig = TypeVar("TScaffoldConfig", bound="BaseScaffoldConfig")
TScaffold = TypeVar("TScaffold", bound="BaseScaffold")


class BaseScaffoldConfig(BaseModel):
    """
    Base configuration class for scaffolds.
    
    This is a minimal base class. Concrete scaffold configs should define
    their own fields based on their specific needs.
    """

    repo_type: Literal["scaffold"] = Field(default="scaffold", description="Repository type identifier")

    @classmethod
    def _load_config_dict(cls, repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load and parse config file from the scaffold directory.
        
        Args:
            repo_name_or_path: Repository name or path to the scaffold directory.
            
        Returns:
            Configuration dictionary.
            
        Raises:
            FileNotFoundError: If config file not found.
            ValueError: If config file is invalid.
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
        
        All templates must be file paths (e.g., "templates/main.j2").
        Template files must exist in the scaffold directory.
        
        Args:
            config_dict: Configuration dictionary.
            repo_name_or_path: Repository name or path to the scaffold directory.
            
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
    def from_repo(cls: Type[TScaffoldConfig], repo_name_or_path: Union[str, Path]) -> TScaffoldConfig:
        """
        Create a config instance from a scaffold repository.
        
        This method loads the configuration from a config.yaml file in the specified directory,
        similar to transformers' from_pretrained() method (we use from_repo in Interaxions).
        
        Args:
            repo_name_or_path: Repository name (e.g., "username/repo") or path to the directory 
                              containing config.yaml. Can be a string or Path object.
        
        Returns:
            Config instance with templates loaded as strings.
        
        Raises:
            FileNotFoundError: If config.yaml is not found in the directory.
            ValueError: If the config file is invalid.
        
        Example:
            >>> config = SWEAgentConfig.from_repo("./my-scaffold")
            >>> # Templates are now loaded as strings in config.templates
        """
        repo_name_or_path = Path(repo_name_or_path)

        # Validate directory
        if not repo_name_or_path.exists():
            raise FileNotFoundError(f"Directory not found: {repo_name_or_path}")

        if not repo_name_or_path.is_dir():
            raise ValueError(f"Path must be a directory: {repo_name_or_path}")

        # Load config dictionary
        config_dict = cls._load_config_dict(repo_name_or_path)

        # Load templates from files
        config_dict = cls._load_templates(config_dict, repo_name_or_path)

        # Create config instance
        return cls(**config_dict)


class BaseScaffold(ABC):
    """
    Base class for scaffolds.

    A scaffold is an instance that encapsulates configuration and knows how to:
    - Validate task parameters.
    - Generate Argo Workflow task objects.
    
    Common task creation methods (implement as needed):
    - create_task(name, model, env, inputs=None, outputs=None, **kwargs)
        Create an Argo Workflow task for this agent.
    """

    config_class: Type[BaseScaffoldConfig] = BaseScaffoldConfig
    config: BaseScaffoldConfig

    def __init__(self, config: BaseScaffoldConfig):
        """
        Initialize the scaffold with a configuration.
        
        Args:
            config: Agent configuration instance.
        """
        self.config = config

    @classmethod
    def from_config(cls: Type[TScaffold], config: BaseScaffoldConfig) -> TScaffold:
        """
        Create an agent instance from a configuration object.
        
        This method provides a transformers-style factory pattern for creating agents.
        It's functionally equivalent to direct instantiation but provides a more
        explicit and conventional API.
        
        Args:
            config: Agent configuration instance.
            
        Returns:
            Agent instance.
        
        Example:
            >>> config = SWEAgentConfig(image="...", ...)
            >>> agent = SWEAgent.from_config(config)
        
        Note:
            This is similar to HuggingFace transformers' from_config() method:
            >>> config = BertConfig()
            >>> model = BertModel.from_config(config)
        """
        return cls(config=config)

    @classmethod
    def from_repo(cls: Type[TScaffold], repo_name_or_path: Union[str, Path]) -> TScaffold:
        """
        Create an agent instance from an agent repository.
        
        This method loads the configuration from a config.yaml file in the specified directory
        and creates an agent instance, similar to transformers' from_pretrained() method
        (we use from_repo in Interaxions).
        
        Args:
            repo_name_or_path: Repository name (e.g., "username/repo") or path to the directory 
                              containing config.yaml. Can be a string or Path object.
        
        Returns:
            Agent instance.
        
        Raises:
            FileNotFoundError: If config.yaml is not found in the directory.
            ValueError: If the config file is invalid.
        
        Example:
            >>> agent = SWEAgent.from_repo("./my-agent")
            >>> task = agent.create_task(context=context)
        """
        config = cls.config_class.from_repo(repo_name_or_path)
        return cls(config=config)

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with the given context.
        
        Templates are stored as strings in config.templates (loaded by from_repo),
        similar to how transformers stores chat_template in tokenizer_config.json.
        
        Args:
            template_name: Name of the template (e.g., "main", "sidecar").
            context: Dictionary of variables to pass to the template.
            
        Returns:
            Rendered template string.
            
        Raises:
            ValueError: If template not found in config.
        
        Example:
            >>> agent = SWEAgent.from_repo("./ix-hub/swe-agent")
            >>> script = agent.render_template("main", {"instance_id": "test-123", ...})
        """
        if not hasattr(self.config, 'templates') or not self.config.templates:
            raise ValueError(f"No templates found in agent config. "
                             f"Agent must be loaded via from_repo() to use templates.")

        if template_name not in self.config.templates:
            available = list(self.config.templates.keys())
            raise ValueError(f"Template '{template_name}' not found in agent config. "
                             f"Available templates: {available}")

        template_str = self.config.templates[template_name]
        template = Template(template_str)
        return template.render(context)

    @abstractmethod
    def create_task(self, job: "XJob", **kwargs: Any) -> "Task":
        """
        Create an Argo Workflow task for this agent.
        
        The agent extracts necessary information from the XJob protocol,
        including model configuration, agent-specific parameters, etc.

        Args:
            job: XJob protocol containing all configuration and runtime information.
                 The agent will extract:
                 - job.model: LLM configuration
                 - job.scaffold.params: Scaffold-specific parameters
                 - job.runtime: Kubernetes/Argo runtime settings
            **kwargs: Additional implementation-specific parameters for extensibility.

        Returns:
            Hera Task object ready for use in a workflow.
            
        Note:
            Concrete implementations can be more specific about what they need from XJob:
            
            def create_task(self, job: XJob, **kwargs: Any) -> Task:
                # Extract info from job
                context = self.build_context(
                    model=job.model,
                    env=...,  # Could load from job.environment if needed
                    **job.scaffold.params
                )
                
                # Auto-generate name from job
                name = f"agent-{job.environment.environment_id}"
                
                # Create task...
        """
        pass
