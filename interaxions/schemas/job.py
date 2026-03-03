from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from interaxions.schemas.workflow import WorkflowConfig
from interaxions.schemas.runtime import RuntimeConfig


class XJob(BaseModel):
    """
    A job is a unit of work that can be executed.

    XJob is intentionally minimal and framework-neutral. It carries:
    - Job identity/metadata (job_id, name, tags, labels)
    - Workflow configuration (which workflow to run, and all workflow-specific params)
    - Runtime configuration (Kubernetes/Argo settings)

    All component configuration (model, scaffold, environment, etc.) is passed
    through workflow.params. The workflow itself defines and validates what params
    it expects, keeping XJob free from assumptions about what a job "should" contain.

    Design Philosophy:
    - XJob defines WHAT to run (workflow + runtime)
    - workflow.params carries HOW to configure it (entirely workflow-defined)
    - Different workflows can have completely different param shapes

    Example:
        >>> from interaxions.schemas import XJob, WorkflowConfig, RuntimeConfig
        >>>
        >>> job = XJob(
        ...     name="swe-bench-django-12345",
        ...     labels={"team": "research"},
        ...     workflow=WorkflowConfig(
        ...         repo_name_or_path="ix-hub/swe-rollout-verify",
        ...         params={
        ...             "scaffold": {
        ...                 "repo_name_or_path": "ix-hub/swe-agent",
        ...                 "extra_params": {"max_iterations": 50}
        ...             },
        ...             "environment": {
        ...                 "repo_name_or_path": "ix-hub/swe-bench",
        ...                 "id": "django__django-12345"
        ...             },
        ...             "model": {
        ...                 "type": "litellm",
        ...                 "provider": "openai",
        ...                 "model": "gpt-4o",
        ...                 "base_url": "https://api.openai.com/v1",
        ...                 "api_key": "sk-..."
        ...             }
        ...         }
        ...     ),
        ...     runtime=RuntimeConfig(namespace="experiments")
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

    # === Identity / Metadata ===
    job_id: Optional[str] = Field(None, description="Unique job identifier (auto-generated if not provided)")
    name: Optional[str] = Field(None, description="Human-readable job name")
    description: Optional[str] = Field(None, description="Job description")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization and search")
    labels: Optional[Dict[str, str]] = Field(None, description="Key-value labels for organization and filtering")

    # === Core (required) ===
    workflow: WorkflowConfig = Field(..., description="Workflow configuration (required)")
    runtime: RuntimeConfig = Field(..., description="Runtime configuration (required)")

    # === Extra ===
    extra_params: Optional[Dict[str, Any]] = Field(None, description="Additional job-level parameters")

    @model_validator(mode='after')
    def generate_job_id(self):
        """Auto-generate job_id if not provided."""
        if self.job_id is None:
            import uuid
            self.job_id = f"job-{uuid.uuid4()}"
        return self
