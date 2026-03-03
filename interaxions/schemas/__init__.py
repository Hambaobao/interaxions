"""
Schema definitions for Interaxions framework.

This module contains Pydantic data models that define schemas/contracts
used throughout the framework.
"""

from interaxions.schemas.job import XJob
from interaxions.schemas.models import (
    Model,
    OpenAIModel,
    AnthropicModel,
    LiteLLMModel,
)
from interaxions.schemas.scaffold import ScaffoldConfig
from interaxions.schemas.environment import EnvironmentConfig
from interaxions.schemas.workflow import WorkflowConfig
from interaxions.schemas.task import Environment
from interaxions.schemas.runtime import RuntimeConfig, Resources

__all__ = [
    # Models
    "Model",
    "OpenAIModel",
    "AnthropicModel",
    "LiteLLMModel",
    # XJob
    "XJob",
    # Component config schemas (standard vocabulary for workflow params)
    "ScaffoldConfig",
    "EnvironmentConfig",
    "WorkflowConfig",
    # Core data schemas
    "Environment",
    # Runtime
    "RuntimeConfig",
    "Resources",
]
