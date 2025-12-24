from typing import Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from interaxions.schemas.models import Model
from interaxions.schemas.scaffold import Scaffold
from interaxions.schemas.environment import Environment
from interaxions.schemas.workflow import Workflow
from interaxions.schemas.runtime import Runtime


class Job(BaseModel):
    """
    A job is a unit of work that can be executed.
    
    Job encapsulates configuration for running an agent-environment interaction
    workflow on Kubernetes/Argo Workflows. It serves as a flexible, serializable
    configuration that can be saved, shared, and executed consistently.
    
    Design Philosophy:
    - Job is a COMPOSABLE schema - users pick what they need
    - Only metadata is required; all components are optional
    - Job defines WHAT to run (components and their configs)
    - Workflow defines HOW to run (execution logic and data flow)
    - Components can internally manage multiple instances (e.g., multi-agent teams)
    
    Flexibility:
    - Use only scaffold for simple agent runs
    - Use scaffold + environment for evaluation
    - Use scaffold + environment + workflow for full orchestration
    - Use only environment for dataset access
    - Mix and match as needed!
    
    Example (Full Configuration):
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
    
    Example (Minimal Configuration - Only Scaffold):
        >>> job = Job(
        ...     name="simple-agent-run",
        ...     model=LiteLLMModel(
        ...         provider="openai",
        ...         model="gpt-4",
        ...         api_key="sk-...",
        ...         base_url="https://api.openai.com/v1"
        ...     ),
        ...     scaffold=Scaffold(repo_name_or_path="swe-agent")
        ... )
    
    Example (Environment Only - Dataset Access):
        >>> job = Job(
        ...     name="dataset-exploration",
        ...     environment=Environment(
        ...         repo_name_or_path="swe-bench",
        ...         environment_id="django-123",
        ...         source="hf",
        ...         params={"dataset": "princeton-nlp/SWE-bench", "split": "test"}
        ...     )
        ... )
    
    Persistence:
        >>> # Save job configuration
        >>> with open("job.json", "w") as f:
        ...     f.write(job.model_dump_json(indent=2))
        >>> 
        >>> # Load job configuration
        >>> with open("job.json", "r") as f:
        ...     job = Job.model_validate_json(f.read())
    """

    # === Metadata (Always Present) ===
    job_id: Optional[str] = Field(None, description="Unique job identifier (auto-generated if not provided)")
    name: Optional[str] = Field(None, description="Human-readable job name")
    description: Optional[str] = Field(None, description="Job description")
    tags: Optional[List[str]] = Field(None, description="Simple tags for categorization and search (e.g., ['tutorial', 'swe-bench', 'high-priority'])")
    labels: Optional[Dict[str, str]] = Field(None, description="Key-value labels for organization and filtering (e.g., {'team': 'research', 'env': 'prod'})")
    created_at: datetime = Field(default_factory=datetime.now, description="Job creation timestamp")
    finished_at: Optional[datetime] = Field(None, description="Job completion timestamp (set when job finishes)")

    # === Component Configuration (All Optional - Mix and Match!) ===
    model: Optional[Model] = Field(None, description="LLM configuration")
    scaffold: Optional[Scaffold] = Field(None, description="Agent scaffold configuration")
    environment: Optional[Environment] = Field(None, description="Environment component configuration")
    workflow: Optional[Workflow] = Field(None, description="Workflow component configuration")
    runtime: Optional[Runtime] = Field(None, description="Runtime configuration (defaults applied if not provided)")

    @model_validator(mode='after')
    def generate_job_id(self):
        """Auto-generate job_id if not provided."""
        if self.job_id is None:
            import uuid
            self.job_id = f"job-{uuid.uuid4()}"
        return self
