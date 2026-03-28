"""
Task interface schemas.

Declares the Argo-level inputs/outputs interface for tasks, and resource
requirements used in container specs.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class TaskArtifact(BaseModel):
    """An artifact input or output for an Argo task."""

    name: str = Field(..., description="Artifact name used in Argo arguments")
    path: str = Field(..., description="Mount path inside the container")
    description: Optional[str] = None


class TaskParameter(BaseModel):
    """A string parameter input or output for an Argo task."""

    name: str
    default: Optional[str] = None
    description: Optional[str] = None


class TaskInputs(BaseModel):
    """Declared inputs for a task (parameters + artifacts)."""

    parameters: List[TaskParameter] = Field(default_factory=list)
    artifacts: List[TaskArtifact] = Field(default_factory=list)


class TaskOutputs(BaseModel):
    """Declared outputs for a task (parameters + artifacts)."""

    parameters: List[TaskParameter] = Field(default_factory=list)
    artifacts: List[TaskArtifact] = Field(default_factory=list)


class Resources(BaseModel):
    """Container resource requests and limits."""

    cpu_request: Optional[Union[float, int, str]] = None
    cpu_limit: Optional[Union[float, int, str]] = None
    memory_request: Optional[str] = None
    memory_limit: Optional[str] = None
    ephemeral_request: Optional[str] = None
    ephemeral_limit: Optional[str] = None
    gpus: Optional[Union[int, str]] = None
    gpu_flag: Optional[str] = Field(default="nvidia.com/gpu")
    custom_resources: Optional[Dict[str, Any]] = None
