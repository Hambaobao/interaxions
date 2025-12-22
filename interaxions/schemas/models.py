"""Model configurations for agents."""

from typing import Annotated, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class LiteLLMModel(BaseModel):
    """
    LiteLLM-based Large Language Model configuration.
    
    Defines the LLM provider, model, and sampling parameters for agent execution.
    This model uses strict validation and will reject any unsupported parameters.
    """

    provider: Literal["openai", "anthropic", "litellm_proxy"] = Field(..., description="The LLM provider")
    model: str = Field(..., description="The model name")
    base_url: str = Field(..., description="The base URL for API")
    api_key: str = Field(..., description="The API key")

    num_retries: int = Field(default=3, ge=0, description="The number of retries")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="The temperature")
    completion_kwargs: Optional[Dict[str, Any]] = Field(default={}, description="The completion kwargs")

    type: Literal["litellm"] = Field(default="litellm", description="The model type")

    model_config = ConfigDict(extra="forbid")


Model = Annotated[Union[LiteLLMModel], Field(discriminator="type")]

