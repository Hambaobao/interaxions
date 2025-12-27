from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Workflow(BaseModel):
    """
    Workflow configuration schema.
    
    Defines how to load a workflow and its runtime parameters.
    
    Example:
        >>> from interaxions.schemas import Workflow
        >>> 
        >>> workflow = Workflow(
        ...     repo_name_or_path="rollout-and-verify",
        ...     revision="v2.0.0",
        ...     params={
        ...         "max_retries": 3,
        ...         "timeout": 3600
        ...     }
        ... )
        >>> 
        >>> # Private repository
        >>> workflow = Workflow(
        ...     repo_name_or_path="company/private-workflow",
        ...     username="user",
        ...     token="ghp_xxxxx",
        ...     params={"max_retries": 5}
        ... )
    """
    repo_name_or_path: str = Field(..., description="The name or path of the workflow repository")
    revision: Optional[str] = Field(None, description="The revision of the workflow repository")
    username: Optional[str] = Field(None, description="Username for private repository authentication")
    token: Optional[str] = Field(None, description="Token/password for private repository authentication")
    params: Dict[str, Any] = Field(default_factory=dict, description="Workflow-specific parameters for create_workflow()")
