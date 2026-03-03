from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EnvironmentConfig(BaseModel):
    """
    Environment component configuration used inside WorkflowConfig.params.

    Describes WHICH environment repo to load the task executor from,
    and WHICH specific instance to process. Does not contain credentials
    or data source routing — those are handled via environment variables
    by the environment repo maintainer.

    Example:
        >>> from interaxions.schemas import EnvironmentConfig
        >>>
        >>> env_config = EnvironmentConfig(
        ...     repo_name_or_path="ix-hub/swe-bench",
        ...     id="django__django-12345",
        ...     params={
        ...         "predictions_path": "/tmp/output/predictions.jsonl"
        ...     }
        ... )
    """

    repo_name_or_path: str = Field(..., description="The name or path of the environment repository")
    revision: Optional[str] = Field(None, description="The revision of the environment repository")
    username: Optional[str] = Field(None, description="Username for private repository authentication")
    token: Optional[str] = Field(None, description="Token/password for private repository authentication")
    id: str = Field(..., description="Environment instance identifier (e.g., 'django__django-12345')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Environment-specific parameters passed to create_task()")
