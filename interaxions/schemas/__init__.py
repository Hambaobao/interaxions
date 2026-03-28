"""
Schema definitions for Interaxions framework.

This module contains Pydantic data models that define schemas/contracts
used throughout the framework.
"""

from interaxions.schemas.job import Job
from interaxions.schemas.models import (
    Model,
    OpenAIModel,
    AnthropicModel,
    LiteLLMModel,
)
from interaxions.schemas.workflow import WorkflowConfig
from interaxions.schemas.workflow_definition import WorkflowDefinition, WorkflowInput, Step
from interaxions.schemas.runtime import RuntimeConfig, Resources
from interaxions.tasks.base_task import TaskInputs, TaskOutputs, TaskArtifact, TaskParameter

__all__ = [
    # Models
    "Model",
    "OpenAIModel",
    "AnthropicModel",
    "LiteLLMModel",
    # Job
    "Job",
    # Workflow
    "WorkflowConfig",
    "WorkflowDefinition",
    "WorkflowInput",
    "Step",
    # Task interface
    "TaskInputs",
    "TaskOutputs",
    "TaskArtifact",
    "TaskParameter",
    # Runtime
    "RuntimeConfig",
    "Resources",
]
