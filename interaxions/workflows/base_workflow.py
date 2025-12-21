"""
Base classes for workflows in Interaxions framework.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Type, TypeVar, Union

import yaml

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from hera.workflows import Workflow

# TypeVar for generic return types
TWorkflowConfig = TypeVar("TWorkflowConfig", bound="BaseWorkflowConfig")
TWorkflow = TypeVar("TWorkflow", bound="BaseWorkflow")


class BaseWorkflowConfig(BaseModel):
    """
    Base configuration class for workflows.
    
    This is a minimal base class. Concrete workflow configs should define
    their own fields based on their specific needs.
    """

    repo_type: Literal["workflow"] = Field(default="workflow", description="Repository type identifier")
    type: str = Field(..., description="Workflow type")

    @classmethod
    def _load_config_dict(cls, repo_name_or_path: "Union[str, Path]") -> Dict[str, Any]:
        """
        Load and parse config file from the workflow directory.
        
        Args:
            repo_name_or_path: Path to the workflow directory.
            
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

        # Load YAML
        with open(config_file, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        if not config_dict:
            raise ValueError(f"Config file is empty: {config_file}")

        return config_dict

    @classmethod
    def from_repo(cls: Type[TWorkflowConfig], repo_name_or_path: "Union[str, Path]") -> TWorkflowConfig:
        """
        Load configuration from a workflow repository.
        
        Args:
            repo_name_or_path: Repository name or path to the workflow directory.
            
        Returns:
            Workflow configuration instance.
        """
        config_dict = cls._load_config_dict(repo_name_or_path)
        return cls(**config_dict)


class BaseWorkflow(ABC):
    """
    Base class for all workflows.
    
    Workflows orchestrate agents and environments into complete Argo Workflows.
    
    Example:
        >>> workflow_template = AutoWorkflow.from_repo("swe-bench-workflow")
        >>> workflow = workflow_template.create_workflow(
        ...     name="swe-bench-run",
        ...     agent=agent,
        ...     environment=env,
        ...     agent_context=context,
        ... )
        >>> workflow.create()
    """

    config_class: Type[BaseWorkflowConfig] = BaseWorkflowConfig
    config: BaseWorkflowConfig

    def __init__(self, config: BaseWorkflowConfig):
        """
        Initialize workflow with configuration.
        
        Args:
            config: Workflow configuration.
        """
        self.config = config

    @classmethod
    def from_repo(cls: Type[TWorkflow], repo_name_or_path: Union[str, Path]) -> TWorkflow:
        """
        Create a workflow instance from a workflow repository.
        
        This method loads the configuration from a config.yaml file in the specified directory
        and creates a workflow instance, similar to transformers' from_pretrained() method
        (we use from_repo in Interaxions).
        
        Args:
            repo_name_or_path: Repository name (e.g., "username/repo") or path to the directory 
                              containing config.yaml. Can be a string or Path object.
        
        Returns:
            Workflow instance.
        
        Raises:
            FileNotFoundError: If config.yaml is not found in the directory.
            ValueError: If the config file is invalid.
        
        Example:
            >>> workflow = RolloutAndVerify.from_repo("./my-workflow")
            >>> argo_workflow = workflow.create_workflow(name="workflow-001", ...)
        """
        config = cls.config_class.from_repo(repo_name_or_path)
        return cls(config=config)

    @abstractmethod
    def create_workflow(self, name: str, **kwargs: Any) -> "Workflow":
        """
        Create an Argo Workflow.
        
        This is an abstract method that must be implemented by all concrete workflows.

        Args:
            name: Workflow name (required by Argo Workflows).
            **kwargs: Implementation-specific parameters.
                     Common parameters include:
                     - agent: Agent instance
                     - environment: Environment instance
                     - namespace: Kubernetes namespace
                     - service_account: Service account name
                     
                     Each implementation defines its own required and optional parameters.
                     See the implementation's docstring for details.

        Returns:
            Hera Workflow object.
            
        Example:
            >>> workflow_template = AutoWorkflow.from_repo("swe-bench-workflow")
            >>> workflow = workflow_template.create_workflow(
            ...     name="swe-bench-run",
            ...     agent=agent,
            ...     environment=env,
            ...     agent_context=context,
            ...     namespace="default"
            ... )
        """
        pass
