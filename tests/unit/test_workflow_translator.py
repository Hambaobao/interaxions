"""
Unit tests for WorkflowTranslator and related helpers.

These tests mock AutoTask.from_repo() and Hera internals so they run
without a real Argo cluster or remote task repos.
"""

from unittest.mock import MagicMock

import pytest

from interaxions.schemas.workflow_definition import WorkflowDefinition, WorkflowInput, Step
from interaxions.schemas.job import Job, WorkflowConfig, RuntimeConfig
from interaxions.tasks.base_task import BaseTaskConfig, TaskArtifact, TaskParameter, TaskOutputs
from interaxions.translator import WorkflowTranslator, _parse_expr

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(params: dict) -> Job:
    return Job(
        workflow=WorkflowConfig(repo_name_or_path="local/wf", params=params),
        runtime=RuntimeConfig(namespace="test"),
    )


def _make_definition(inputs=None, steps=None) -> WorkflowDefinition:
    return WorkflowDefinition(
        type="test-wf",
        inputs=inputs or [],
        steps=steps or [],
    )


def _make_mock_task(output_artifacts=None, output_parameters=None):
    """Build a mock task instance with the given declared outputs."""
    config = MagicMock(spec=BaseTaskConfig)
    outputs = TaskOutputs(
        artifacts=[TaskArtifact(name=a, path=f"/tmp/{a}") for a in (output_artifacts or [])],
        parameters=[TaskParameter(name=p) for p in (output_parameters or [])],
    )
    config.outputs = outputs

    task_instance = MagicMock()
    task_instance.config = config
    return task_instance


# ---------------------------------------------------------------------------
# _parse_expr
# ---------------------------------------------------------------------------


class TestParseExpr:

    def test_valid_template_returns_expr(self):
        assert _parse_expr("${{ inputs.foo }}") == "inputs.foo"

    def test_valid_template_with_extra_spaces(self):
        assert _parse_expr("${{  steps.a.outputs.result  }}") == "steps.a.outputs.result"

    def test_literal_string_returns_none(self):
        assert _parse_expr("gold") is None

    def test_non_string_returns_none(self):
        assert _parse_expr(42) is None
        assert _parse_expr(None) is None
        assert _parse_expr({"key": "val"}) is None

    def test_partial_template_returns_none(self):
        # Not a full-string template
        assert _parse_expr("prefix ${{ inputs.foo }}") is None


# ---------------------------------------------------------------------------
# WorkflowTranslator._resolve_inputs
# ---------------------------------------------------------------------------


class TestResolveInputs:

    def setup_method(self):
        self.translator = WorkflowTranslator()

    def test_value_from_params(self):
        definition = _make_definition(inputs=[
            WorkflowInput(name="msg", type="string", required=True),
        ])
        job = _make_job({"msg": "hello"})
        resolved = self.translator._resolve_inputs(definition, job)
        assert resolved["msg"] == "hello"

    def test_default_used_when_not_in_params(self):
        definition = _make_definition(inputs=[
            WorkflowInput(name="limit", type="integer", required=False, default="50"),
        ])
        job = _make_job({})
        resolved = self.translator._resolve_inputs(definition, job)
        assert resolved["limit"] == "50"

    def test_params_takes_precedence_over_default(self):
        definition = _make_definition(inputs=[
            WorkflowInput(name="limit", type="integer", required=False, default="50"),
        ])
        job = _make_job({"limit": "200"})
        resolved = self.translator._resolve_inputs(definition, job)
        assert resolved["limit"] == "200"

    def test_required_missing_raises(self):
        definition = _make_definition(inputs=[
            WorkflowInput(name="instance_id", type="string", required=True),
        ])
        job = _make_job({})
        with pytest.raises(ValueError, match="Required workflow input 'instance_id'"):
            self.translator._resolve_inputs(definition, job)

    def test_optional_without_default_not_in_resolved(self):
        definition = _make_definition(inputs=[
            WorkflowInput(name="optional_key", type="string", required=False),
        ])
        job = _make_job({})
        resolved = self.translator._resolve_inputs(definition, job)
        assert "optional_key" not in resolved

    def test_multiple_inputs(self):
        definition = _make_definition(inputs=[
            WorkflowInput(name="a", required=True),
            WorkflowInput(name="b", required=False, default="default_b"),
            WorkflowInput(name="c", required=True),
        ])
        job = _make_job({"a": "val_a", "c": "val_c"})
        resolved = self.translator._resolve_inputs(definition, job)
        assert resolved == {"a": "val_a", "b": "default_b", "c": "val_c"}


# ---------------------------------------------------------------------------
# WorkflowTranslator._extract_output_types
# ---------------------------------------------------------------------------


class TestExtractOutputTypes:

    def setup_method(self):
        self.translator = WorkflowTranslator()

    def test_artifact_outputs(self):
        mock_task = _make_mock_task(output_artifacts=["result", "logs"])
        types = self.translator._extract_output_types(mock_task)
        assert types == {"result": "artifact", "logs": "artifact"}

    def test_parameter_outputs(self):
        mock_task = _make_mock_task(output_parameters=["status", "count"])
        types = self.translator._extract_output_types(mock_task)
        assert types == {"status": "parameter", "count": "parameter"}

    def test_mixed_outputs(self):
        mock_task = _make_mock_task(output_artifacts=["data"], output_parameters=["code"])
        types = self.translator._extract_output_types(mock_task)
        assert types == {"data": "artifact", "code": "parameter"}

    def test_empty_outputs(self):
        mock_task = _make_mock_task()
        types = self.translator._extract_output_types(mock_task)
        assert types == {}

    def test_no_outputs_attribute(self):
        mock_task = MagicMock()
        del mock_task.config.outputs  # remove the attribute
        mock_task.config = MagicMock(spec=[])  # config with no attributes
        types = self.translator._extract_output_types(mock_task)
        assert types == {}


# ---------------------------------------------------------------------------
# WorkflowTranslator._resolve_step_output_ref
# ---------------------------------------------------------------------------


class TestResolveStepOutputRef:

    def setup_method(self):
        self.translator = WorkflowTranslator()

    def test_artifact_ref_calls_get_artifact(self):
        src_task = MagicMock()
        artifact_arg = MagicMock()
        src_task.get_artifact.return_value = artifact_arg

        step_hera_tasks = {"fetch": src_task}
        step_output_types = {"fetch": {"result": "artifact"}}

        result = self.translator._resolve_step_output_ref(
            "steps.fetch.outputs.result",
            "agent",
            step_hera_tasks,
            step_output_types,
        )

        src_task.get_artifact.assert_called_once_with("result")
        assert result is artifact_arg

    def test_parameter_ref_calls_get_parameter(self):
        src_task = MagicMock()
        param_arg = MagicMock()
        src_task.get_parameter.return_value = param_arg

        step_hera_tasks = {"fetch": src_task}
        step_output_types = {"fetch": {"status": "parameter"}}

        result = self.translator._resolve_step_output_ref(
            "steps.fetch.outputs.status",
            "agent",
            step_hera_tasks,
            step_output_types,
        )

        src_task.get_parameter.assert_called_once_with("status")
        assert result is param_arg

    def test_unknown_output_defaults_to_artifact(self):
        src_task = MagicMock()
        step_hera_tasks = {"fetch": src_task}
        step_output_types = {"fetch": {}}  # no declared outputs

        self.translator._resolve_step_output_ref(
            "steps.fetch.outputs.unknown",
            "agent",
            step_hera_tasks,
            step_output_types,
        )
        src_task.get_artifact.assert_called_once_with("unknown")

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="invalid cross-step reference"):
            self.translator._resolve_step_output_ref(
                "steps.fetch.result",  # missing "outputs"
                "agent",
                {},
                {},
            )

    def test_unknown_step_raises(self):
        with pytest.raises(ValueError, match="references output of step 'fetch'"):
            self.translator._resolve_step_output_ref(
                "steps.fetch.outputs.result",
                "agent",
                {},  # fetch not yet processed
                {},
            )


# ---------------------------------------------------------------------------
# WorkflowTranslator._resolve_value
# ---------------------------------------------------------------------------


class TestResolveValue:

    def setup_method(self):
        self.translator = WorkflowTranslator()

    def test_literal_passthrough(self):
        result = self.translator._resolve_value("gold", {}, {})
        assert result == "gold"

    def test_inputs_ref_resolved(self):
        resolved_inputs = {"limit": "100"}
        result = self.translator._resolve_value("${{ inputs.limit }}", resolved_inputs, {})
        assert result == "100"

    def test_non_string_passthrough(self):
        assert self.translator._resolve_value(42, {}, {}) == 42
        assert self.translator._resolve_value(None, {}, {}) is None


# ---------------------------------------------------------------------------
# WorkflowTranslator._process_step (with mocked AutoTask)
# ---------------------------------------------------------------------------


class TestProcessStep:
    """Test _process_step with a fully mocked AutoTask."""

    def setup_method(self):
        self.translator = WorkflowTranslator()

    def _make_hera_task(self, name="test-step"):
        hera_task = MagicMock()
        hera_task.name = name
        hera_task.arguments = None
        hera_task.dependencies = None
        return hera_task

    def test_literal_uses_and_kwargs_passed(self):
        mock_task_instance = _make_mock_task()
        hera_task = self._make_hera_task()
        mock_task_instance.create_task.return_value = hera_task

        mock_auto_task = MagicMock()
        mock_auto_task.from_repo.return_value = mock_task_instance

        step = Step(**{
            "id": "step-a",
            "uses": "local/my-task",
            "with": {
                "message": "hello",
                "count": 3
            },
        })

        result_task, output_types = self.translator._process_step(
            step,
            resolved_inputs={},
            step_hera_tasks={},
            step_output_types={},
            AutoTask=mock_auto_task,
        )

        mock_auto_task.from_repo.assert_called_once_with("local/my-task")
        mock_task_instance.create_task.assert_called_once_with(message="hello", count=3)
        assert result_task is hera_task

    def test_inputs_ref_resolved_to_kwarg(self):
        mock_task_instance = _make_mock_task()
        hera_task = self._make_hera_task()
        mock_task_instance.create_task.return_value = hera_task

        mock_auto_task = MagicMock()
        mock_auto_task.from_repo.return_value = mock_task_instance

        step = Step(**{
            "id": "step-a",
            "uses": "local/my-task",
            "with": {
                "model": "${{ inputs.model }}"
            },
        })
        resolved_inputs = {"model": {"provider": "openai", "model": "gpt-4o"}}

        self.translator._process_step(
            step,
            resolved_inputs=resolved_inputs,
            step_hera_tasks={},
            step_output_types={},
            AutoTask=mock_auto_task,
        )

        import json
        mock_task_instance.create_task.assert_called_once_with(model=json.dumps({"provider": "openai", "model": "gpt-4o"}))

    def test_dict_value_json_serialised(self):
        mock_task_instance = _make_mock_task()
        hera_task = self._make_hera_task()
        mock_task_instance.create_task.return_value = hera_task

        mock_auto_task = MagicMock()
        mock_auto_task.from_repo.return_value = mock_task_instance

        step = Step(**{
            "id": "step-a",
            "uses": "local/my-task",
            "with": {
                "cfg": "${{ inputs.cfg }}"
            },
        })
        cfg = {"key": "val"}
        resolved_inputs = {"cfg": cfg}

        self.translator._process_step(
            step,
            resolved_inputs=resolved_inputs,
            step_hera_tasks={},
            step_output_types={},
            AutoTask=mock_auto_task,
        )

        import json
        call_kwargs = mock_task_instance.create_task.call_args.kwargs
        assert call_kwargs["cfg"] == json.dumps(cfg)

    def test_steps_ref_becomes_argo_argument(self):
        src_hera_task = MagicMock()
        artifact_arg = MagicMock()
        src_hera_task.get_artifact.return_value = artifact_arg

        mock_task_instance = _make_mock_task()
        hera_task = self._make_hera_task()
        hera_task.arguments = None
        mock_task_instance.create_task.return_value = hera_task

        mock_auto_task = MagicMock()
        mock_auto_task.from_repo.return_value = mock_task_instance

        step = Step(**{
            "id": "step-b",
            "uses": "local/my-task",
            "needs": ["step-a"],
            "with": {
                "data": "${{ steps.step-a.outputs.result }}"
            },
        })

        result_task, _ = self.translator._process_step(
            step,
            resolved_inputs={},
            step_hera_tasks={"step-a": src_hera_task},
            step_output_types={"step-a": {
                "result": "artifact"
            }},
            AutoTask=mock_auto_task,
        )

        # Artifact argument attached; create_task called with no kwargs
        mock_task_instance.create_task.assert_called_once_with()
        assert artifact_arg in result_task.arguments

    def test_needs_sets_dependencies(self):
        mock_task_instance = _make_mock_task()
        hera_task = self._make_hera_task()
        mock_task_instance.create_task.return_value = hera_task

        mock_auto_task = MagicMock()
        mock_auto_task.from_repo.return_value = mock_task_instance

        step = Step(**{
            "id": "step-b",
            "uses": "local/my-task",
            "needs": ["step-a", "step-pre"],
            "with": {},
        })

        self.translator._process_step(
            step,
            resolved_inputs={},
            step_hera_tasks={
                "step-a": MagicMock(),
                "step-pre": MagicMock()
            },
            step_output_types={},
            AutoTask=mock_auto_task,
        )

        assert hera_task.dependencies == ["step-a", "step-pre"]

    def test_unresolved_inputs_ref_raises(self):
        mock_auto_task = MagicMock()
        mock_auto_task.from_repo.return_value = _make_mock_task()

        step = Step(**{
            "id": "step-a",
            "uses": "local/my-task",
            "with": {
                "x": "${{ inputs.missing_key }}"
            },
        })

        with pytest.raises(ValueError, match="inputs.missing_key"):
            self.translator._process_step(
                step,
                resolved_inputs={},  # missing_key not present
                step_hera_tasks={},
                step_output_types={},
                AutoTask=mock_auto_task,
            )

    def test_unknown_expression_raises(self):
        mock_auto_task = MagicMock()
        mock_auto_task.from_repo.return_value = _make_mock_task()

        step = Step(**{
            "id": "step-a",
            "uses": "local/my-task",
            "with": {
                "x": "${{ env.SECRET }}"
            },  # unsupported prefix
        })

        with pytest.raises(ValueError, match="unrecognised expression"):
            self.translator._process_step(
                step,
                resolved_inputs={},
                step_hera_tasks={},
                step_output_types={},
                AutoTask=mock_auto_task,
            )
