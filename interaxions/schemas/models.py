"""
Model configurations for agents.
"""

from typing import Annotated, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class OpenAIModel(BaseModel):
    """
    OpenAI-based Large Language Model configuration.

    Defines the OpenAI model and sampling parameters for agent execution.
    This model uses strict validation and will reject any unsupported parameters.
    """

    type: Literal["openai"] = Field(default="openai", description="The model type")

    model: str = Field(..., description="The model name (e.g., gpt-4, gpt-3.5-turbo)")
    api_key: str = Field(..., description="The OpenAI API key")
    base_url: Optional[str] = Field(default="https://api.openai.com/v1", description="The base URL for OpenAI API")

    num_retries: int = Field(default=3, ge=0, description="The number of retries")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="The temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="The maximum number of tokens to generate")
    completion_kwargs: Optional[Dict[str, Any]] = Field(default={}, description="The completion kwargs")

    model_config = ConfigDict(extra="forbid")


class AnthropicModel(BaseModel):
    """
    Anthropic-based Large Language Model configuration.

    Defines the Anthropic Claude model and sampling parameters for agent execution.
    This model uses strict validation and will reject any unsupported parameters.
    """

    type: Literal["anthropic"] = Field(default="anthropic", description="The model type")

    model: str = Field(..., description="The model name (e.g., claude-sonnet-4-5, claude-opus-4-5)")
    api_key: str = Field(..., description="The Anthropic API key")
    base_url: Optional[str] = Field(default="https://api.anthropic.com", description="The base URL for Anthropic API")

    num_retries: int = Field(default=3, ge=0, description="The number of retries")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="The temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="The maximum number of tokens to generate")
    completion_kwargs: Optional[Dict[str, Any]] = Field(default={}, description="The completion kwargs")

    model_config = ConfigDict(extra="forbid")


class LiteLLMModel(BaseModel):
    """
    LiteLLM-based Large Language Model configuration.

    Defines the LLM provider, model, and sampling parameters for agent execution.
    This model uses strict validation and will reject any unsupported parameters.
    """

    type: Literal["litellm"] = Field(default="litellm", description="The model type")

    provider: Literal["openai", "anthropic", "litellm_proxy"] = Field(..., description="The LLM provider")
    model: str = Field(..., description="The model name")
    base_url: str = Field(..., description="The base URL for API")
    api_key: str = Field(..., description="The API key")

    num_retries: int = Field(default=3, ge=0, description="The number of retries")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="The temperature")
    completion_kwargs: Optional[Dict[str, Any]] = Field(default={}, description="The completion kwargs")

    model_config = ConfigDict(extra="forbid")


Model = Annotated[Union[
    OpenAIModel,
    AnthropicModel,
    LiteLLMModel,
], Field(discriminator="type")]
