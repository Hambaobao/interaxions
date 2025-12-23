from typing import Any, Dict, List, Literal, Optional
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from interaxions.schemas.models import Model


class Scaffold(BaseModel):
    """
    Scaffold configuration schema.
    
    A scaffold defines how to construct agent component(s). It may internally create:
    - Single agent (e.g., one SWE agent)
    - Multiple agents (e.g., coder + reviewer + coordinator)
    - Complex agent systems with custom orchestration
    
    The Job doesn't care about internal structure - that's decided by the scaffold implementation.
    """
    repo_name_or_path: str = Field(..., description="The name or path of the agent scaffold repository")
    revision: Optional[str] = Field(None, description="The revision of the repository")
    params: Dict[str, Any] = Field(default_factory=dict, description="Scaffold-specific parameters for build_context() and create_task()")


class Environment(BaseModel):
    """
    Environment configuration schema.
    
    Defines how to load an environment, its data source, and runtime parameters.
    """
    repo_name_or_path: str = Field(..., description="The name or path of the environment repository")
    revision: Optional[str] = Field(None, description="The revision of the environment repository")
    environment_id: str = Field(..., description="The environment id")
    source: str = Field(..., description="Data source type (e.g., 'hf', 'oss', 'local', 'custom')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Environment parameters including data source parameters (e.g., dataset/split for HF) and task parameters (e.g., predictions_path)")


class Workflow(BaseModel):
    """
    Workflow configuration schema.
    
    Defines how to load a workflow and its runtime parameters.
    """
    repo_name_or_path: str = Field(..., description="The name or path of the workflow repository")
    revision: Optional[str] = Field(None, description="The revision of the workflow repository")
    params: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific parameters for create_workflow()")


class Runtime(BaseModel):
    """
    Runtime configuration schema.
    
    Defines Kubernetes/Argo Workflows runtime settings.
    """
    namespace: str = Field(default="default", description="Kubernetes namespace")
    service_account: Optional[str] = Field(None, description="Service account name")
    image_pull_policy: Literal["Always", "IfNotPresent"] = Field(default="IfNotPresent", description="Image pull policy")
    ttl_seconds_after_finished: Optional[int] = Field(None, description="TTL (seconds) for workflow cleanup after completion")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional runtime parameters (e.g., labels, annotations, node_selector, tolerations, priority_class_name)")


class Job(BaseModel):
    """
    A job is a unit of work that can be executed.
    
    Job encapsulates all configuration needed to run an agent-environment interaction
    workflow on Kubernetes/Argo Workflows. It serves as a serializable configuration
    that can be saved, shared, and executed consistently.
    
    Design Philosophy:
    - Job defines WHAT to run (components and their configs)
    - Workflow defines HOW to run (execution logic and data flow)
    - Components can internally manage multiple instances (e.g., multi-agent teams)
    
    Example:
        >>> from interaxions.schemas import Job, Scaffold, Environment, Workflow, Runtime
        >>> from interaxions.schemas import LiteLLMModel
        >>> 
        >>> job = Job(
        ...     name="django-bugfix-experiment",
        ...     description="Test SWE agent on Django issue #12345",
        ...     tags=["experiment", "swe-bench", "django"],
        ...     labels={"team": "research", "priority": "high"},
        ...     model=LiteLLMModel(
        ...         provider="openai",
        ...         model="gpt-4",
        ...         api_key="sk-...",
        ...         base_url="https://api.openai.com/v1"
        ...     ),
        ...     scaffold=Scaffold(
        ...         repo_name_or_path="swe-agent",
        ...         params={
        ...             "sweagent_config": "default.yaml",
        ...             "max_iterations": 10
        ...         }
        ...     ),
        ...     environment=Environment(
        ...         repo_name_or_path="swe-bench",
        ...         environment_id="django__django-12345",
        ...         source="hf",
        ...         params={
        ...             "dataset": "princeton-nlp/SWE-bench",
        ...             "split": "test"
        ...         }
        ...     ),
        ...     workflow=Workflow(repo_name_or_path="rollout-and-verify"),
        ...     runtime=Runtime(namespace="experiments")
        ... )
        >>> 
        >>> # Job ID is auto-generated
        >>> print(job.job_id)  # e.g., "job-a3f2e8c1"
        >>> 
        >>> # Save job configuration
        >>> with open("job.json", "w") as f:
        ...     f.write(job.model_dump_json(indent=2))
        >>> 
        >>> # Load job configuration
        >>> with open("job.json", "r") as f:
        ...     job = Job.model_validate_json(f.read())
    """

    # === Metadata ===
    job_id: Optional[str] = Field(None, description="Unique job identifier (auto-generated if not provided)")
    name: Optional[str] = Field(None, description="Human-readable job name")
    description: Optional[str] = Field(None, description="Job description")
    tags: Optional[List[str]] = Field(None, description="Simple tags for categorization and search (e.g., ['tutorial', 'swe-bench', 'high-priority'])")
    labels: Optional[Dict[str, str]] = Field(None, description="Key-value labels for organization and filtering (e.g., {'team': 'research', 'env': 'prod'})")
    created_at: datetime = Field(default_factory=datetime.now, description="Job creation timestamp")
    finished_at: Optional[datetime] = Field(None, description="Job completion timestamp (set when job finishes)")

    # === Component Configuration ===
    model: Model = Field(..., description="LLM configuration")
    scaffold: Scaffold = Field(..., description="Agent scaffold configuration")
    environment: Environment = Field(..., description="Environment component configuration")
    workflow: Workflow = Field(..., description="Workflow component configuration")
    runtime: Runtime = Field(default_factory=Runtime, description="Runtime configuration")

    @model_validator(mode='after')
    def generate_job_id(self):
        """Auto-generate job_id if not provided."""
        if self.job_id is None:
            import uuid
            self.job_id = f"job-{uuid.uuid4()}"
        return self
