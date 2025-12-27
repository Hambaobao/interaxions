from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Scaffold(BaseModel):
    """
    Scaffold configuration schema.
    
    A scaffold defines how to construct agent component(s). It may internally create:
    - Single agent (e.g., one SWE agent)
    - Multiple agents (e.g., coder + reviewer + coordinator)
    - Complex agent systems with custom orchestration
    
    The XJob doesn't care about internal structure - that's decided by the scaffold implementation.
    
    Example:
        >>> from interaxions.schemas import Scaffold
        >>> 
        >>> scaffold = Scaffold(
        ...     repo_name_or_path="swe-agent",
        ...     revision="v1.0.0",
        ...     params={
        ...         "sweagent_config": "default.yaml",
        ...         "max_iterations": 10
        ...     }
        ... )
        >>> 
        >>> # Private repository
        >>> scaffold = Scaffold(
        ...     repo_name_or_path="company/private-agent",
        ...     username="user",
        ...     token="ghp_xxxxx",
        ...     params={"max_iterations": 10}
        ... )
    """
    repo_name_or_path: str = Field(..., description="The name or path of the agent scaffold repository")
    revision: Optional[str] = Field(None, description="The revision of the repository")
    username: Optional[str] = Field(None, description="Username for private repository authentication")
    token: Optional[str] = Field(None, description="Token/password for private repository authentication")
    params: Dict[str, Any] = Field(default_factory=dict, description="Scaffold-specific parameters for build_context() and create_task()")
