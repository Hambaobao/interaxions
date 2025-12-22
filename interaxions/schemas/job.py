from typing import Any, Dict, Optional
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from interaxions.schemas.models import Model


class ScaffoldProto(BaseModel):
    """
    Protocol for an agent scaffold.
    
    A scaffold defines how to construct agent component(s). It may internally create:
    - Single agent (e.g., one SWE agent)
    - Multiple agents (e.g., coder + reviewer + coordinator)
    - Complex agent systems with custom orchestration
    
    The Job doesn't care about internal structure - that's decided by the scaffold implementation.
    """
    repo_name_or_path: str = Field(..., description="The name or path of the agent scaffold repository")
    revision: Optional[str] = Field(None, description="The revision of the repository")
    params: Dict[str, Any] = Field(default_factory=dict, description="Scaffold-specific parameters for build_context() and create_task()")


class EnvironmentProto(BaseModel):
    """
    Protocol for an environment component.
    
    Defines how to load an environment, its data source, and runtime parameters.
    """
    repo_name_or_path: str = Field(..., description="The name or path of the environment repository")
    revision: Optional[str] = Field(None, description="The revision of the environment repository")
    environment_id: str = Field(..., description="The environment id")

    # Data source configuration
    source: str = Field(..., description="Data source type (e.g., 'hf', 'oss', 'local', 'custom')")
    source_params: Dict[str, Any] = Field(default_factory=dict, description="Source-specific parameters (e.g., dataset/split for HF, bucket/key for OSS)")

    # Environment task parameters
    params: Dict[str, Any] = Field(default_factory=dict, description="Environment-specific parameters for create_task()")


class WorkflowProto(BaseModel):
    """
    Protocol for a workflow component.
    
    Defines how to load a workflow and its runtime parameters.
    """
    repo_name_or_path: str = Field(..., description="The name or path of the workflow repository")
    revision: Optional[str] = Field(None, description="The revision of the workflow repository")
    params: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific parameters for create_workflow()")


class RuntimeProto(BaseModel):
    """
    Protocol for runtime configuration.
    
    Defines Kubernetes/Argo Workflows runtime settings.
    """
    namespace: str = Field(default="default", description="Kubernetes namespace")
    service_account: Optional[str] = Field(None, description="Service account name")
    image_pull_secrets: Optional[list[str]] = Field(None, description="Image pull secret names")
    ttl_seconds_after_finished: Optional[int] = Field(None, description="TTL (seconds) for workflow cleanup after completion")


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
        >>> from interaxions.schemas import Job, ScaffoldProto, EnvironmentProto, WorkflowProto, RuntimeProto
        >>> from interaxions.schemas import LiteLLMModel
        >>> 
        >>> job = Job(
        ...     name="django-bugfix-experiment",
        ...     description="Test SWE agent on Django issue #12345",
        ...     tags={"team": "research", "priority": "high"},
        ...     model=LiteLLMModel(
        ...         provider="openai",
        ...         model="gpt-4",
        ...         api_key="sk-...",
        ...         base_url="https://api.openai.com/v1"
        ...     ),
        ...     scaffold=ScaffoldProto(
        ...         repo_name_or_path="swe-agent",
        ...         params={
        ...             "sweagent_config": "default.yaml",
        ...             "max_iterations": 10
        ...         }
        ...     ),
        ...     environment=EnvironmentProto(
        ...         repo_name_or_path="swe-bench",
        ...         environment_id="django__django-12345",
        ...         source="hf",
        ...         source_params={
        ...             "dataset": "princeton-nlp/SWE-bench",
        ...             "split": "test"
        ...         }
        ...     ),
        ...     workflow=WorkflowProto(repo_name_or_path="rollout-and-verify"),
        ...     runtime=RuntimeProto(namespace="experiments")
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
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags for filtering and organization")
    created_at: datetime = Field(default_factory=datetime.now, description="Job creation timestamp")

    # === Component Configuration ===
    model: Model = Field(..., description="LLM configuration")
    scaffold: ScaffoldProto = Field(..., description="Agent scaffold configuration")
    environment: EnvironmentProto = Field(..., description="Environment component configuration")
    workflow: WorkflowProto = Field(..., description="Workflow component configuration")
    runtime: RuntimeProto = Field(default_factory=RuntimeProto, description="Runtime configuration")

    @model_validator(mode='after')
    def generate_job_id(self):
        """Auto-generate job_id if not provided."""
        if self.job_id is None:
            import uuid
            self.job_id = f"job-{uuid.uuid4().hex[:8]}"
        return self
