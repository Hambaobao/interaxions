from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Environment(BaseModel):
    """
    Environment configuration schema.
    
    Defines how to load an environment, its data source, and runtime parameters.
    
    Example:
        >>> from interaxions.schemas import Environment
        >>> 
        >>> # HuggingFace environment
        >>> env = Environment(
        ...     repo_name_or_path="swe-bench",
        ...     environment_id="django__django-12345",
        ...     source="hf",
        ...     params={
        ...         "dataset": "princeton-nlp/SWE-bench",
        ...         "split": "test",
        ...         "predictions_path": "gold"
        ...     }
        ... )
        >>> 
        >>> # Private repository with OSS
        >>> env = Environment(
        ...     repo_name_or_path="company/private-bench",
        ...     environment_id="task-001",
        ...     source="oss",
        ...     username="user",
        ...     token="glpat-xxxxx",
        ...     params={
        ...         "dataset": "swe-bench-data",
        ...         "split": "test",
        ...         "oss_region": "cn-hangzhou",
        ...         "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
        ...         "oss_access_key_id": "your-key-id",
        ...         "oss_access_key_secret": "your-secret"
        ...     }
        ... )
    """
    repo_name_or_path: str = Field(..., description="The name or path of the environment repository")
    revision: Optional[str] = Field(None, description="The revision of the environment repository")
    username: Optional[str] = Field(None, description="Username for private repository authentication")
    token: Optional[str] = Field(None, description="Token/password for private repository authentication")
    environment_id: str = Field(..., description="The environment id")
    source: str = Field(..., description="Data source type (e.g., 'hf', 'oss', 'local', 'custom')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Environment parameters including data source parameters (e.g., dataset/split for HF) and task parameters (e.g., predictions_path)")
