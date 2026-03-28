"""
Workflow schemas.

WorkflowDefinition: parsed from a workflow repo's workflow.yaml.
WorkflowInput / Step: building blocks of the declarative DAG definition.
"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


class WorkflowInput(BaseModel):
    """Declares a named input parameter for the workflow."""

    name: str
    type: str = Field(
        default="string",
        description="string | integer | boolean | object | task",
    )
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None


class Step(BaseModel):
    """A single step in the workflow DAG."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique step identifier")
    uses: str = Field(
        ...,
        description="Task repo path, or ${{ inputs.xxx }} expression",
    )
    needs: List[str] = Field(
        default_factory=list,
        description="Step IDs that must complete before this step runs",
    )
    with_: Dict[str, Any] = Field(
        default_factory=dict,
        alias="with",
        description=(
            "Parameters and artifacts passed to the task. Values may be:\n"
            "  - Literal values\n"
            "  - ${{ inputs.NAME }} — resolved from Job.workflow.params\n"
            "  - ${{ steps.ID.outputs.NAME }} — Argo artifact/parameter from a prior step"
        ),
    )


class WorkflowDefinition(BaseModel):
    """
    Declarative definition of a workflow, parsed from workflow.yaml.

    Serves as both repo metadata (repo_type, type) and the DAG specification
    (inputs, steps). AutoWorkflow.from_repo() returns a DeclarativeWorkflow
    when this file is present.

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

        steps:
          - id: fetch
            uses: ix-hub/SWE-bench-fetch
            with:
              instance_id: ${{ inputs.instance_id }}

          - id: agent
            uses: ${{ inputs.agent_task }}
            needs: [fetch]
            with:
              instance_data: ${{ steps.fetch.outputs.instance_data }}
    """

    repo_type: Literal["workflow"] = "workflow"
    type: str
    name: Optional[str] = None
    inputs: List[WorkflowInput] = Field(default_factory=list)
    steps: List[Step] = Field(...)

    @classmethod
    def from_yaml(cls, path: Path) -> "WorkflowDefinition":
        """Load and parse a workflow.yaml file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
