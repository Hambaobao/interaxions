"""
Pydantic models for the declarative workflow.yaml format.

A workflow.yaml file defines a DAG of tasks in a GitHub-Actions-like style.
The framework parses this into a WorkflowDefinition and translates it into
a Hera Workflow for execution on Argo.

Example workflow.yaml:

    repo_type: workflow
    type: swe-rollout-verify
    name: SWE Rollout & Verify

    inputs:
      - name: instance_id
        type: string
        required: true
      - name: agent_task
        type: task
        required: true
        default: ix-hub/SWE-agent

    steps:
      - id: fetch
        uses: ix-hub/SWE-bench-fetch
        with:
          instance_id: ${{ inputs.instance_id }}

      - id: agent
        uses: ${{ inputs.agent_task }}
        needs: [fetch]
        with:
          model: ${{ inputs.model }}
          instance_data: ${{ steps.fetch.outputs.instance_data }}

      - id: verify
        uses: ix-hub/SWE-bench-verify
        needs: [agent]
        with:
          instance_id: ${{ inputs.instance_id }}
          result: ${{ steps.agent.outputs.result }}
"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


class WorkflowInput(BaseModel):
    """Declares a named input parameter for the workflow."""

    name: str = Field(..., description="Input parameter name")
    type: str = Field(
        default="string",
        description="Value type: string | integer | boolean | object | task",
    )
    required: bool = Field(default=True, description="Whether this input must be provided")
    default: Optional[Any] = Field(default=None, description="Default value if not provided")
    description: Optional[str] = Field(default=None, description="Human-readable description")


class Step(BaseModel):
    """A single step in the workflow DAG."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique step identifier, used in ${{ steps.ID.outputs.X }}")
    uses: str = Field(
        ...,
        description="Task repo to use. Can be a literal repo path or ${{ inputs.xxx }}",
    )
    needs: List[str] = Field(
        default_factory=list,
        description="List of step IDs that must complete before this step runs",
    )
    with_: Dict[str, Any] = Field(
        default_factory=dict,
        alias="with",
        description=(
            "Parameters and artifacts to pass to the task. Values can be:\n"
            "  - Literal values\n"
            "  - ${{ inputs.NAME }} — resolved from Job.workflow.params\n"
            "  - ${{ steps.ID.outputs.NAME }} — Argo artifact/parameter from a previous step"
        ),
    )


class WorkflowDefinition(BaseModel):
    """
    Complete declarative definition of a workflow, parsed from workflow.yaml.

    Serves as both the repository metadata (repo_type, type) and the
    DAG specification (inputs, steps).
    """

    repo_type: Literal["workflow"] = Field(default="workflow")
    type: str = Field(..., description="Workflow type identifier")
    name: Optional[str] = Field(default=None, description="Human-readable workflow name")
    inputs: List[WorkflowInput] = Field(default_factory=list)
    steps: List[Step] = Field(..., description="Ordered list of DAG steps")

    @classmethod
    def from_yaml(cls, path: Path) -> "WorkflowDefinition":
        """Load and parse a workflow.yaml file into a WorkflowDefinition."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
