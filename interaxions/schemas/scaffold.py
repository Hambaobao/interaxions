from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ScaffoldConfig(BaseModel):
    """
    Scaffold component configuration used inside WorkflowConfig.params.

    Describes WHICH scaffold repo to load the task executor from,
    and any scaffold-specific runtime parameters.

    Example:
        >>> from interaxions.schemas import ScaffoldConfig
        >>>
        >>> scaffold_config = ScaffoldConfig(
        ...     repo_name_or_path="ix-hub/swe-agent",
        ...     params={
        ...         "max_iterations": 50,
        ...         "sweagent_config": "default.yaml"
        ...     }
        ... )
    """

    repo_name_or_path: str = Field(..., description="The name or path of the scaffold repository")
    revision: Optional[str] = Field(None, description="The revision of the repository")
    username: Optional[str] = Field(None, description="Username for private repository authentication")
    token: Optional[str] = Field(None, description="Token/password for private repository authentication")
    params: Dict[str, Any] = Field(default_factory=dict, description="Scaffold-specific parameters passed to create_task()")
