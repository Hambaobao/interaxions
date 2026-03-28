"""
WorkflowTranslator: converts a declarative WorkflowDefinition + Job into a Hera Workflow.

This is the core of the declarative workflow system. It handles:
  - Resolving ${{ inputs.xxx }} expressions from Job.workflow.params
  - Loading tasks via AutoTask.from_repo()
  - Wiring Argo artifact/parameter passing for ${{ steps.ID.outputs.NAME }} references
  - Assembling the final Hera Workflow with a DAG entrypoint
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from hera.workflows import DAG, Workflow
from hera.workflows.models import Backoff, PodGC, RetryStrategy, TTLStrategy

from interaxions.schemas.workflow import WorkflowDefinition, Step
from interaxions.schemas.job import Job
from interaxions.schemas.runtime import RuntimeConfig, TTLConfig, RetryConfig

# Matches ${{ some.expression }}
_EXPR_RE = re.compile(r"^\$\{\{\s*(.*?)\s*\}\}$")


def _parse_expr(value: Any) -> Optional[str]:
    """Return the expression string if value is a ${{ ... }} template, else None."""
    if not isinstance(value, str):
        return None
    m = _EXPR_RE.match(value)
    return m.group(1).strip() if m else None


class WorkflowTranslator:
    """
    Translates a WorkflowDefinition + Job into a Hera Workflow object.

    Usage:
        translator = WorkflowTranslator()
        hera_wf = translator.translate(definition, job)
        hera_wf.create()  # submit to Argo
    """

    def translate(self, definition: WorkflowDefinition, job: Job) -> Workflow:
        """
        Build a Hera Workflow from a declarative WorkflowDefinition and a Job.

        Steps:
          1. Resolve workflow inputs from job.workflow.params
          2. For each step (in declaration order):
             a. Resolve `uses:` to a concrete task repo path
             b. Load the task via AutoTask.from_repo()
             c. Separate with: values into Python kwargs vs Argo arguments
             d. Call task.create_task(**kwargs) → Hera Task
             e. Attach Argo artifact/parameter arguments from previous steps
             f. Set step dependencies from needs:
          3. Return the assembled Hera Workflow

        Args:
            definition: Parsed WorkflowDefinition from workflow.yaml.
            job: Job carrying runtime config and workflow.params.

        Returns:
            Hera Workflow ready for .create() submission.

        Raises:
            ValueError: If a required input is missing or a step reference is invalid.
        """
        # Lazy import to avoid circular dependency at module level
        from interaxions.hub.auto import AutoTask

        resolved_inputs = self._resolve_inputs(definition, job)

        # Maps step_id → Hera Task (for cross-step argument wiring)
        step_hera_tasks: Dict[str, Any] = {}
        # Maps step_id → {output_name: "artifact" | "parameter"}
        step_output_types: Dict[str, Dict[str, str]] = {}

        rt = job.runtime

        with Workflow(
            generate_name=f"{definition.type}-",
            namespace=rt.namespace,
            service_account_name=rt.service_account,
            entrypoint="entrypoint",
            labels=job.labels,
            annotations=job.annotations,
            active_deadline_seconds=rt.active_deadline_seconds,
            ttl_strategy=_build_ttl(rt.ttl) if rt.ttl else None,
            retry_strategy=_build_retry(rt.retry) if rt.retry else None,
            dns_policy=rt.dns_policy,
            pod_gc=PodGC(strategy=rt.pod_gc_strategy) if rt.pod_gc_strategy else None,
            pod_priority_class_name=rt.pod_priority_class_name,
            node_selector=rt.node_selector,
            tolerations=rt.tolerations,
        ) as wf:
            with DAG(name="entrypoint"):
                for step in definition.steps:
                    hera_task, output_types = self._process_step(
                        step,
                        resolved_inputs,
                        step_hera_tasks,
                        step_output_types,
                        AutoTask,
                    )
                    step_hera_tasks[step.id] = hera_task
                    step_output_types[step.id] = output_types

        return wf

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_inputs(
        self, definition: WorkflowDefinition, job: Job
    ) -> Dict[str, Any]:
        """Resolve all workflow inputs from job.workflow.params."""
        resolved: Dict[str, Any] = {}
        for inp in definition.inputs:
            if inp.name in job.workflow.params:
                resolved[inp.name] = job.workflow.params[inp.name]
            elif inp.default is not None:
                resolved[inp.name] = inp.default
            elif inp.required:
                raise ValueError(
                    f"Required workflow input '{inp.name}' not provided "
                    f"in job.workflow.params. Available keys: "
                    f"{list(job.workflow.params.keys())}"
                )
        return resolved

    def _process_step(
        self,
        step: Step,
        resolved_inputs: Dict[str, Any],
        step_hera_tasks: Dict[str, Any],
        step_output_types: Dict[str, Dict[str, str]],
        AutoTask: Any,
    ) -> Tuple[Any, Dict[str, str]]:
        """Process a single step: load task, resolve with:, create Hera Task."""
        # 1. Resolve `uses:` to a concrete repo path
        uses = self._resolve_value(step.uses, resolved_inputs, step_hera_tasks)
        if not isinstance(uses, str):
            raise ValueError(
                f"Step '{step.id}': uses must resolve to a string repo path, "
                f"got {type(uses).__name__}"
            )

        # 2. Load task
        task_instance = AutoTask.from_repo(uses)

        # 3. Separate with: values into Python kwargs and Argo-level arguments
        kwargs: Dict[str, Any] = {}
        argo_arguments: List[Any] = []

        for key, raw_value in step.with_.items():
            expr = _parse_expr(raw_value)
            if expr is None:
                # Literal value
                kwargs[key] = raw_value
            elif expr.startswith("inputs."):
                # Resolved from workflow inputs
                param_name = expr[len("inputs."):]
                value = resolved_inputs.get(param_name)
                if value is None:
                    raise ValueError(
                        f"Step '{step.id}': with.{key} references "
                        f"${{{{ inputs.{param_name} }}}} which is not resolved."
                    )
                # Objects are JSON-serialised to string (Argo parameters are strings)
                kwargs[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
            elif expr.startswith("steps."):
                # Cross-step artifact/parameter reference → Argo argument
                arg = self._resolve_step_output_ref(
                    expr, step.id, step_hera_tasks, step_output_types
                )
                argo_arguments.append(arg)
            else:
                raise ValueError(
                    f"Step '{step.id}': unrecognised expression '${{{{ {expr} }}}}'. "
                    "Expected 'inputs.NAME' or 'steps.STEP_ID.outputs.NAME'."
                )

        # 4. Create Hera Task (kwargs only; Argo arguments added below)
        hera_task = task_instance.create_task(**kwargs)

        # 5. Attach Argo artifact/parameter arguments
        if argo_arguments:
            existing = list(hera_task.arguments or [])
            hera_task.arguments = existing + argo_arguments

        # 6. Set dependencies
        if step.needs:
            hera_task.dependencies = step.needs

        # 7. Record output types for downstream steps
        output_types = self._extract_output_types(task_instance)

        return hera_task, output_types

    def _resolve_value(
        self,
        value: Any,
        resolved_inputs: Dict[str, Any],
        step_hera_tasks: Dict[str, Any],
    ) -> Any:
        """Resolve a single value that may contain a ${{ }} expression."""
        expr = _parse_expr(value)
        if expr is None:
            return value
        if expr.startswith("inputs."):
            param_name = expr[len("inputs."):]
            return resolved_inputs.get(param_name, value)
        return value

    def _resolve_step_output_ref(
        self,
        expr: str,
        current_step_id: str,
        step_hera_tasks: Dict[str, Any],
        step_output_types: Dict[str, Dict[str, str]],
    ) -> Any:
        """
        Resolve a steps.STEP_ID.outputs.NAME expression to a Hera argument.

        expr format: "steps.STEP_ID.outputs.NAME"
        """
        parts = expr.split(".")
        if len(parts) != 4 or parts[2] != "outputs":
            raise ValueError(
                f"Step '{current_step_id}': invalid cross-step reference "
                f"'${{{{ {expr} }}}}'. Expected format: "
                "'steps.STEP_ID.outputs.ARTIFACT_OR_PARAM_NAME'."
            )

        src_step_id = parts[1]
        output_name = parts[3]

        if src_step_id not in step_hera_tasks:
            raise ValueError(
                f"Step '{current_step_id}': references output of step "
                f"'{src_step_id}' which has not been processed yet. "
                f"Add '{src_step_id}' to the needs: list."
            )

        src_task = step_hera_tasks[src_step_id]
        output_type = step_output_types.get(src_step_id, {}).get(output_name, "artifact")

        if output_type == "parameter":
            return src_task.get_parameter(output_name)
        return src_task.get_artifact(output_name)

    def _extract_output_types(self, task_instance: Any) -> Dict[str, str]:
        """Build a {output_name: 'artifact'|'parameter'} map from task config."""
        types: Dict[str, str] = {}
        if hasattr(task_instance.config, "outputs"):
            for a in task_instance.config.outputs.artifacts:
                types[a.name] = "artifact"
            for p in task_instance.config.outputs.parameters:
                types[p.name] = "parameter"
        return types


# ---------------------------------------------------------------------------
# Hera model builders
# ---------------------------------------------------------------------------


def _build_ttl(ttl: TTLConfig) -> TTLStrategy:
    """Convert TTLConfig → Hera TTLStrategy."""
    return TTLStrategy(**ttl.model_dump(exclude_none=True))


def _build_retry(retry: RetryConfig) -> RetryStrategy:
    """Convert RetryConfig → Hera RetryStrategy."""
    backoff = None
    if retry.backoff:
        backoff = Backoff(duration=retry.backoff.duration, factor=retry.backoff.factor)
    return RetryStrategy(limit=retry.limit, retry_policy=retry.policy, backoff=backoff)
