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
    from interaxions.schemas.job import XJob

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
    def _load_templates(cls, config_dict: Dict[str, Any], repo_name_or_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load template files referenced in config.
        
        All templates must be file paths (e.g., "templates/main.j2").
        Template files must exist in the workflow directory.
        
        Args:
            config_dict: Configuration dictionary.
            repo_name_or_path: Repository name or path to the workflow directory.
            
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
    def from_repo(cls: Type[TWorkflowConfig], repo_name_or_path: Union[str, Path]) -> TWorkflowConfig:
        """
        Load configuration from a workflow repository.
        
        Args:
            repo_name_or_path: Path to the workflow directory.
            
        Returns:
            Workflow configuration instance.
        """
        config_dict = cls._load_config_dict(repo_name_or_path)
        config_dict = cls._load_templates(config_dict, repo_name_or_path)
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
            repo_name_or_path: Path to the directory containing config.yaml. 
                              Can be a string or Path object.
        
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
    def create_workflow(self, job: "XJob", **kwargs: Any) -> "Workflow":
        """
        Create an Argo Workflow from an XJob specification.
        
        The workflow orchestrates the entire execution by:
        1. Loading agent and environment from job specifications
        2. Creating agent and environment tasks by passing the job to them
        3. Defining task dependencies and workflow structure
        
        This method serves as the entry point for executing a complete job.

        Args:
            job: XJob protocol containing all configuration and runtime information.
                 The workflow will:
                 - Load scaffold from job.scaffold (repo_name_or_path, revision)
                 - Load environment from job.environment (repo_name_or_path, revision, source)
                 - Pass job to scaffold.create_task(job) and env.create_task(job)
                 - Use job.runtime for Kubernetes/Argo settings
                 - Extract job.workflow.params for workflow-specific parameters
            **kwargs: Additional implementation-specific parameters for extensibility.

        Returns:
            Hera Workflow object ready for submission to Argo.
            
        Example:
            >>> from interaxions.schemas import XJob, ...
            >>> from interaxions.hub import AutoWorkflow
            >>> 
            >>> job = XJob(...)
            >>> workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
            >>> workflow = workflow_template.create_workflow(job)
            >>> workflow.create()  # Submit to Argo
            
        Note:
            Concrete implementations typically follow this pattern:
            
            def create_workflow(self, job: XJob, **kwargs: Any) -> Workflow:
                from interaxions.hub import AutoScaffold, AutoEnvironmentFactory
                
                # 1. Load components from job
                scaffold = AutoScaffold.from_repo(job.scaffold.repo_name_or_path, job.scaffold.revision)
                env_factory = AutoEnvironmentFactory.from_repo(...)
                env = env_factory.get_from_hf(...) or env_factory.get_from_oss(...)
                
                # 2. Create tasks (they will extract info from job)
                scaffold_task = scaffold.create_task(job)
                env_task = env.create_task(job)
                
                # 3. Build workflow
                name = f"workflow-{job.environment.environment_id}"
                with Workflow(name=name, namespace=job.runtime.namespace) as w:
                    scaffold_task >> env_task
                
                return w
        """
        pass
