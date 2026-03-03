from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WorkflowConfig(BaseModel):
    """
    Workflow configuration in XJob.

    Specifies which workflow repo to load and passes all workflow-specific
    parameters (including scaffold, environment, model configs, etc.) via
    the params field. The workflow itself defines and validates what params
    it expects.

    Example:
        >>> from interaxions.schemas import WorkflowConfig
        >>>
        >>> # Workflow params are entirely defined by the workflow implementation
        >>> workflow_config = WorkflowConfig(
        ...     repo_name_or_path="ix-hub/swe-rollout-verify",
        ...     params={
        ...         "scaffold": {
        ...             "repo_name_or_path": "ix-hub/swe-agent",
        ...             "extra_params": {"max_iterations": 50}
        ...         },
        ...         "environment": {
        ...             "repo_name_or_path": "ix-hub/swe-bench",
        ...             "id": "django__django-12345"
        ...         },
        ...         "model": {
        ...             "type": "litellm",
        ...             "provider": "openai",
        ...             "model": "gpt-4o",
        ...             "base_url": "https://api.openai.com/v1",
        ...             "api_key": "sk-..."
        ...         }
        ...     }
        ... )
    """

    repo_name_or_path: str = Field(..., description="The name or path of the workflow repository")
    revision: Optional[str] = Field(None, description="The revision of the workflow repository")
    username: Optional[str] = Field(None, description="Username for private repository authentication")
    token: Optional[str] = Field(None, description="Token/password for private repository authentication")
    params: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific parameters. The workflow defines and validates its own params schema.")
