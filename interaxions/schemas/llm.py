"""
LLM model configuration schemas.
"""

from typing import Annotated, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class OpenAIModel(BaseModel):
    """OpenAI model configuration."""

    type: Literal["openai"] = Field(default="openai")
    model: str = Field(..., description="Model name, e.g. gpt-4o")
    api_key: str
    base_url: Optional[str] = Field(default="https://api.openai.com/v1")
    num_retries: int = Field(default=3, ge=0)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    completion_kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class AnthropicModel(BaseModel):
    """Anthropic model configuration."""

    type: Literal["anthropic"] = Field(default="anthropic")
    model: str = Field(..., description="Model name, e.g. claude-sonnet-4-6")
    api_key: str
    base_url: Optional[str] = Field(default="https://api.anthropic.com")
    num_retries: int = Field(default=3, ge=0)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    completion_kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class LiteLLMModel(BaseModel):
    """LiteLLM model configuration (multi-provider)."""

    type: Literal["litellm"] = Field(default="litellm")
    provider: Literal["openai", "anthropic", "litellm_proxy"] = Field(...)
    model: str
    base_url: str
    api_key: str
    num_retries: int = Field(default=3, ge=0)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    completion_kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


Model = Annotated[
    Union[OpenAIModel, AnthropicModel, LiteLLMModel],
    Field(discriminator="type"),
]
