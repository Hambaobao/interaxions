from typing import Optional, Literal, Union, Annotated, Dict, Any

from pydantic import BaseModel, Field


class HFEEnvironmentSource(BaseModel):
    """
    HuggingFace source configuration schema.
    """
    type: Literal["hf"] = "hf"

    dataset: str = Field(..., description="The name of the dataset")
    split: str = Field(..., description="The name of the split")
    revision: Optional[str] = Field(None, description="The revision of the dataset")

    token: Optional[str] = Field(None, description="The token of huggingface")


class OSSEnvironmentSource(BaseModel):
    """
    OSS source configuration schema.
    """
    type: Literal["oss"] = "oss"

    dataset: str = Field(..., description="The name of the dataset")
    split: str = Field(..., description="The name of the split")
    revision: Optional[str] = Field(None, description="The revision of the dataset")

    oss_region: str = Field(..., description="The region of the OSS")
    oss_endpoint: str = Field(..., description="The endpoint of the OSS")
    oss_access_key_id: str = Field(..., description="The access key id of the OSS")
    oss_access_key_secret: str = Field(..., description="The access key secret of the OSS")


EnvironmentSource = Annotated[Union[
    HFEEnvironmentSource,
    OSSEnvironmentSource,
], Field(discriminator="type")]


class Environment(BaseModel):
    """
    Environment configuration schema.
    
    Defines how to load an environment, its data source, and runtime parameters.
    
    Example:
        >>> from interaxions.schemas import Environment, HFEEnvironmentSource, OSSEnvironmentSource
        >>> 
        >>> # HuggingFace environment
        >>> env = Environment(
        ...     repo_name_or_path="swe-bench",
        ...     environment_id="django__django-12345",
        ...     environment_source=HFEEnvironmentSource(
        ...         dataset="princeton-nlp/SWE-bench",
        ...         split="test",
        ...     ),
        ... )
        >>> 
        >>> # HuggingFace environment with extra params
        >>> env = Environment(
        ...     repo_name_or_path="swe-bench",
        ...     environment_id="django__django-12345",
        ...     environment_source=HFEEnvironmentSource(
        ...         dataset="princeton-nlp/SWE-bench",
        ...         split="test",
        ...     ),
        ...     extra_params={
        ...         "predictions_path": "gold",
        ...         "timeout": 300
        ...     }
        ... )
        >>> 
        >>> # Private repository with OSS
        >>> env = Environment(
        ...     repo_name_or_path="company/private-bench",
        ...     username="user",
        ...     token="glpat-xxxxx",
        ...     environment_id="task-001",
        ...     environment_source=OSSEnvironmentSource(
        ...         dataset="swe-bench-data",
        ...         split="test",
        ...         oss_region="cn-hangzhou",
        ...         oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
        ...         oss_access_key_id="your-key-id",
        ...         oss_access_key_secret="your-secret"
        ...     ),
        ... )
    """
    repo_name_or_path: str = Field(..., description="The name or path of the environment repository")
    revision: Optional[str] = Field(None, description="The revision of the environment repository")
    username: Optional[str] = Field(None, description="Username for private repository authentication")
    token: Optional[str] = Field(None, description="Token/password for private repository authentication")
    environment_id: str = Field(..., description="The environment id")
    source: EnvironmentSource = Field(..., description="The environment source")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Extra parameters for the environment")
