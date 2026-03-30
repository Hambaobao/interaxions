"""
Integration tests for AutoWorkflow dynamic loading from local repositories.
"""

import pytest

from interaxions import AutoWorkflow
from interaxions.workflows.declarative import DeclarativeWorkflow
from interaxions.schemas.workflow import WorkflowDefinition


@pytest.mark.integration
class TestAutoWorkflowDeclarative:
    """Tests for loading a declarative (workflow.yaml) workflow."""

    def test_load_from_string_path(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(str(mock_declarative_workflow_repo))
        assert workflow is not None
        assert isinstance(workflow, DeclarativeWorkflow)

    def test_load_from_path_object(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert isinstance(workflow, DeclarativeWorkflow)

    def test_has_definition(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert hasattr(workflow, "_definition")
        assert isinstance(workflow._definition, WorkflowDefinition)

    def test_definition_type_matches_yaml(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert workflow._definition.type == "test-declarative"

    def test_definition_name_matches_yaml(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert workflow._definition.name == "Test Declarative Workflow"

    def test_definition_inputs_loaded(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        input_names = [i.name for i in workflow._definition.inputs]
        assert "task_a" in input_names
        assert "message" in input_names
        assert "required_input" in input_names

    def test_definition_inputs_defaults(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        message_input = next(i for i in workflow._definition.inputs if i.name == "message")
        assert message_input.default == "hello"
        assert message_input.required is False

    def test_definition_required_input(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        required = next(i for i in workflow._definition.inputs if i.name == "required_input")
        assert required.required is True

    def test_definition_steps_loaded(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        steps = workflow._definition.steps
        assert len(steps) == 2
        assert steps[0].id == "step-a"
        assert steps[1].id == "step-b"

    def test_step_uses_expression(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert workflow._definition.steps[0].uses == "${{ inputs.task_a }}"

    def test_step_needs(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert workflow._definition.steps[1].needs == ["step-a"]

    def test_step_with_block(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert workflow._definition.steps[1].with_["data"] == "${{ steps.step-a.outputs.result }}"

    def test_has_create_workflow_method(self, mock_declarative_workflow_repo):
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert hasattr(workflow, "create_workflow")
        assert callable(workflow.create_workflow)

    def test_invalid_path_raises(self, tmp_path):
        """Loading from a directory with no workflow.yaml raises FileNotFoundError."""
        empty = tmp_path / "empty-workflow"
        empty.mkdir()
        with pytest.raises(FileNotFoundError):
            AutoWorkflow.from_repo(str(empty))

    def test_path_to_file_raises(self, mock_declarative_workflow_repo):
        """Passing a file path (not a directory) raises an error."""
        with pytest.raises(Exception):
            AutoWorkflow.from_repo(str(mock_declarative_workflow_repo / "workflow.yaml"))


@pytest.mark.integration
class TestWorkflowDefinitionFromYaml:
    """Tests for WorkflowDefinition.from_yaml()."""

    def test_from_yaml_parses_correctly(self, mock_declarative_workflow_repo):
        definition = WorkflowDefinition.from_yaml(
            mock_declarative_workflow_repo / "workflow.yaml"
        )
        assert definition.type == "test-declarative"
        assert len(definition.steps) == 2

    def test_from_yaml_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            WorkflowDefinition.from_yaml(tmp_path / "workflow.yaml")

    def test_step_with_alias_parsed(self, mock_declarative_workflow_repo):
        definition = WorkflowDefinition.from_yaml(
            mock_declarative_workflow_repo / "workflow.yaml"
        )
        step_a = definition.steps[0]
        assert "message" in step_a.with_
        assert "label" in step_a.with_
