"""
Job schema — the top-level unit of work submitted to the platform.
"""

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from interaxions.schemas.runtime import RuntimeConfig


class WorkflowConfig(BaseModel):
    """
    Reference to a workflow repo + parameters to pass to it.

    repo_name_or_path identifies the workflow (remote hub path or local path),
    and params carries all workflow-level inputs. The workflow's workflow.yaml
    declares which params it expects; Job makes no assumptions about their shape.

    Example:
        WorkflowConfig(
            repo_name_or_path="ix-hub/swe-rollout-verify",
            params={
                "instance_id": "django__django-12345",
                "agent_task": "ix-hub/SWE-agent",
                "model": {"type": "litellm", "provider": "anthropic", ...},
            },
        )
    """

    repo_name_or_path: str = Field(..., description="Hub path or local path to the workflow repo")
    revision: Optional[str] = Field(None, description="Git revision (tag, branch, commit hash)")
    username: Optional[str] = Field(None, description="Username for private repo auth")
    token: Optional[str] = Field(None, description="Token for private repo auth")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow inputs — keys and shape defined by the workflow's workflow.yaml",
    )


class Job(BaseModel):
    """
    A unit of work: which workflow to run, with what params, on what infrastructure.

    Job is intentionally thin. It carries:
      - Identity / metadata (job_id, name, tags, labels)
      - Workflow reference + inputs (workflow)
      - Kubernetes / Argo runtime settings (runtime)

    All component configuration (tasks, models, data sources, etc.) lives in
    workflow.params. The workflow itself defines what params it expects.

    Example:
        job = Job(
            name="swe-bench-django-12345",
            labels={"team": "research"},
            workflow=WorkflowConfig(
                repo_name_or_path="ix-hub/swe-rollout-verify",
                params={
                    "instance_id": "django__django-12345",
                    "agent_task": "ix-hub/SWE-agent",
                    "model": {"type": "litellm", ...},
                },
            ),
            runtime=RuntimeConfig(namespace="experiments"),
        )
    """

    # Identity
    job_id: Optional[str] = Field(None, description="Unique identifier (auto-generated if omitted)")
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None

    # Core (required)
    workflow: WorkflowConfig = Field(...)
    runtime: RuntimeConfig = Field(...)

    # Escape hatch for platform-level metadata
    extra_params: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _auto_job_id(self) -> "Job":
        if self.job_id is None:
            self.job_id = f"job-{uuid.uuid4()}"
        return self
