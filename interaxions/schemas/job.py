from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from interaxions.schemas.models import Model
from interaxions.schemas.scaffold import Scaffold
from interaxions.schemas.environment import Environment
from interaxions.schemas.workflow import Workflow
from interaxions.schemas.runtime import Runtime


class XJob(BaseModel):
    """
    A job is a unit of work that can be executed.
    
    XJob encapsulates configuration for running an agent-environment interaction
    workflow on Kubernetes/Argo Workflows. It serves as a flexible, serializable
    configuration that can be saved, shared, and executed consistently.
    
    Design Philosophy:
    - XJob is a COMPOSABLE schema - mix and match components as needed
    - Workflow and Runtime are required for execution
    - XJob defines WHAT to run (components and their configs)
    - Workflow defines HOW to run (execution logic and data flow)
    - Components can internally manage multiple instances (e.g., multi-agent teams)
    
    Required Components:
    - workflow: Defines the execution orchestration (required)
    - runtime: Kubernetes/Argo runtime settings (required, must specify namespace)
    
    Optional Components:
    - model: LLM configuration (if agents need it)
    - scaffold: Agent implementation
    - environment: Test environment or dataset
    
    Example (Full Configuration):
        >>> from interaxions.schemas import XJob, Scaffold, Environment, Workflow, Runtime
        >>> from interaxions.schemas import LiteLLMModel
        >>> 
        >>> job = XJob(
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
        >>> job = XJob(
        ...     name="simple-agent-run",
        ...     model=LiteLLMModel(
        ...         provider="openai",
        ...         model="gpt-4",
        ...         api_key="sk-...",
        ...         base_url="https://api.openai.com/v1"
        ...     ),
        ...     scaffold=Scaffold(repo_name_or_path="swe-agent"),
        ...     workflow=Workflow(repo_name_or_path="rollout-and-verify"),
        ...     runtime=Runtime(namespace="default")
        ... )
    
    Example (Minimal with Custom Runtime):
        >>> job = XJob(
        ...     name="production-job",
        ...     workflow=Workflow(repo_name_or_path="simple-workflow"),
        ...     runtime=Runtime(
        ...         namespace="production",
        ...         service_account="argo-workflow",
        ...         ttl_seconds_after_finished=7200
        ...     )
        ... )
    
    Persistence:
        >>> # Save job configuration
        >>> with open("job.json", "w") as f:
        ...     f.write(job.model_dump_json(indent=2))
        >>> 
        >>> # Load job configuration
        >>> with open("job.json", "r") as f:
        ...     job = XJob.model_validate_json(f.read())
    """

    # === Metadata (Configuration Only) ===
    job_id: Optional[str] = Field(None, description="Unique job identifier (auto-generated if not provided)")
    name: Optional[str] = Field(None, description="Human-readable job name")
    description: Optional[str] = Field(None, description="XJob description")
    tags: Optional[List[str]] = Field(None, description="Simple tags for categorization and search (e.g., ['tutorial', 'swe-bench', 'high-priority'])")
    labels: Optional[Dict[str, str]] = Field(None, description="Key-value labels for organization and filtering (e.g., {'team': 'research', 'env': 'prod'})")

    # === Necessary Component Configuration ===
    workflow: Workflow = Field(..., description="Workflow component configuration (required for execution)")
    runtime: Runtime = Field(..., description="Runtime configuration (required, specify namespace)")

    # === Optional Component Configuration (Mix and Match!) ===
    model: Optional[Model] = Field(None, description="LLM configuration")
    scaffold: Optional[Scaffold] = Field(None, description="Agent scaffold configuration")
    environment: Optional[Environment] = Field(None, description="Environment component configuration")

    @model_validator(mode='after')
    def generate_job_id(self):
        """Auto-generate job_id if not provided."""
        if self.job_id is None:
            import uuid
            self.job_id = f"job-{uuid.uuid4()}"
        return self
