"""
Integration tests for AutoWorkflow dynamic loading from local repositories.

All tests use the test-workflow mock repo in tests/fixtures/mock_repos/.
Built-in workflows have been removed; all components are loaded from
external repositories via local paths or remote Git URLs.
"""

import pytest

from interaxions import AutoWorkflow
from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig
from interaxions.workflows.declarative import DeclarativeWorkflow
from interaxions.schemas.workflow import WorkflowDefinition


@pytest.mark.integration
class TestAutoWorkflowFromLocalPath:
    """Tests for loading a workflow from a local path."""

    def test_load_from_string_path(self, mock_workflow_repo):
        """AutoWorkflow.from_repo() accepts a string path."""
        workflow = AutoWorkflow.from_repo(str(mock_workflow_repo))

        assert workflow is not None
        assert isinstance(workflow, BaseWorkflow)

    def test_load_from_path_object(self, mock_workflow_repo):
        """AutoWorkflow.from_repo() accepts a Path object."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert workflow is not None
        assert isinstance(workflow, BaseWorkflow)

    def test_has_config(self, mock_workflow_repo):
        """Loaded workflow has a populated config attribute."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert hasattr(workflow, "config")
        assert workflow.config is not None
        assert isinstance(workflow.config, BaseWorkflowConfig)

    def test_config_type_matches_yaml(self, mock_workflow_repo):
        """Config type matches the value in config.yaml."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert workflow.config.type == "test-workflow"

    def test_templates_loaded_from_yaml(self, mock_workflow_repo):
        """Templates referenced in config.yaml are loaded as strings."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert hasattr(workflow.config, "templates")
        assert workflow.config.templates is not None

        templates = workflow.config.templates
        assert "main" in templates
        assert "verification" in templates
        # Check that they contain the expected template content
        assert isinstance(templates["main"], str)
        assert isinstance(templates["verification"], str)
        assert len(templates["main"]) > 0

    def test_has_create_workflow_method(self, mock_workflow_repo):
        """Loaded workflow has callable create_workflow method."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert hasattr(workflow, "create_workflow")
        assert callable(workflow.create_workflow)

    def test_has_from_repo_class_method(self, mock_workflow_repo):
        """Workflow class exposes from_repo class method."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert hasattr(workflow, "from_repo")
        assert callable(workflow.from_repo)


@pytest.mark.integration
class TestAutoWorkflowDiscovery:
    """Tests for the automatic class discovery in ix.py."""

    def test_discovers_correct_class(self, mock_workflow_repo):
        """AutoWorkflow discovers the single BaseWorkflow subclass in ix.py."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)
        assert type(workflow).__name__ == "TestWorkflow"

    def test_invalid_path_raises(self, tmp_path):
        """Loading from a directory with no config.yaml raises FileNotFoundError."""
        empty = tmp_path / "empty-workflow"
        empty.mkdir()

        with pytest.raises(FileNotFoundError):
            AutoWorkflow.from_repo(str(empty))

    def test_path_to_file_raises(self, mock_workflow_repo):
        """Passing a file path (not a directory) raises an error."""
        ix_file = mock_workflow_repo / "ix.py"
        assert ix_file.exists()

        with pytest.raises(Exception):
            AutoWorkflow.from_repo(str(ix_file))

    def test_no_base_class_subclass_raises(self, tmp_path):
        """Repository without a BaseWorkflow subclass raises ValueError."""
        repo = tmp_path / "bad-workflow"
        repo.mkdir()
        (repo / "config.yaml").write_text("repo_type: workflow\ntype: bad\n")
        (repo / "ix.py").write_text("# no classes here\n")

        with pytest.raises(ValueError, match="No class inheriting from BaseWorkflow"):
            AutoWorkflow.from_repo(str(repo))

    def test_multiple_base_classes_raises(self, tmp_path):
        """Repository with multiple BaseWorkflow subclasses raises ValueError."""
        repo = tmp_path / "multi-workflow"
        repo.mkdir()
        (repo / "config.yaml").write_text("repo_type: workflow\ntype: multi\n")
        (repo / "ix.py").write_text(
            "from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig\n"
            "from pydantic import Field\n"
            "class _C(BaseWorkflowConfig):\n    type: str = 'multi'\n"
            "class WorkflowA(BaseWorkflow):\n    config_class = _C\n"
            "    def create_workflow(self, job, **kw): pass\n"
            "class WorkflowB(BaseWorkflow):\n    config_class = _C\n"
            "    def create_workflow(self, job, **kw): pass\n"
        )

        with pytest.raises(ValueError, match="Multiple classes"):
            AutoWorkflow.from_repo(str(repo))


@pytest.mark.integration
class TestBaseWorkflowConfig:
    """Tests for BaseWorkflowConfig loading logic."""

    def test_loads_config_from_yaml(self, mock_workflow_repo):
        config = BaseWorkflowConfig._load_config_dict(mock_workflow_repo)
        assert config["type"] == "test-workflow"
        assert "templates" in config

    def test_template_paths_in_yaml(self, mock_workflow_repo):
        """Before loading, templates are file paths (strings)."""
        config = BaseWorkflowConfig._load_config_dict(mock_workflow_repo)
        assert isinstance(config["templates"]["main"], str)
        # Values should be relative paths, not loaded content yet
        assert config["templates"]["main"].endswith(".j2")

    def test_load_templates_replaces_paths_with_content(self, mock_workflow_repo):
        """After _load_templates(), template values become file content strings."""
        config = BaseWorkflowConfig._load_config_dict(mock_workflow_repo)
        config = BaseWorkflowConfig._load_templates(config, mock_workflow_repo)

        assert isinstance(config["templates"]["main"], str)
        assert isinstance(config["templates"]["verification"], str)
        # Content should be actual template text, not a path
        assert not config["templates"]["main"].endswith(".j2")

    def test_missing_config_raises(self, tmp_path):
        empty = tmp_path / "no-config"
        empty.mkdir()

        with pytest.raises(FileNotFoundError):
            BaseWorkflowConfig._load_config_dict(empty)

    def test_missing_template_file_raises(self, tmp_path):
        repo = tmp_path / "bad-templates"
        repo.mkdir()
        (repo / "config.yaml").write_text(
            "repo_type: workflow\ntype: test\ntemplates:\n  main: templates/missing.j2\n"
        )

        config = BaseWorkflowConfig._load_config_dict(repo)
        with pytest.raises(FileNotFoundError):
            BaseWorkflowConfig._load_templates(config, repo)


@pytest.mark.integration
class TestAutoWorkflowDeclarative:
    """Tests for loading a declarative (workflow.yaml) workflow."""

    def test_returns_declarative_workflow_instance(self, mock_declarative_workflow_repo):
        """AutoWorkflow.from_repo() returns a DeclarativeWorkflow when workflow.yaml exists."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert isinstance(workflow, DeclarativeWorkflow)

    def test_also_subclass_of_base_workflow(self, mock_declarative_workflow_repo):
        """DeclarativeWorkflow is still a BaseWorkflow."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert isinstance(workflow, BaseWorkflow)

    def test_has_definition(self, mock_declarative_workflow_repo):
        """Loaded workflow has a _definition attribute of type WorkflowDefinition."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert hasattr(workflow, "_definition")
        assert isinstance(workflow._definition, WorkflowDefinition)

    def test_definition_type_matches_yaml(self, mock_declarative_workflow_repo):
        """WorkflowDefinition.type matches the value in workflow.yaml."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert workflow._definition.type == "test-declarative"

    def test_definition_name_matches_yaml(self, mock_declarative_workflow_repo):
        """WorkflowDefinition.name matches the value in workflow.yaml."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert workflow._definition.name == "Test Declarative Workflow"

    def test_definition_inputs_loaded(self, mock_declarative_workflow_repo):
        """WorkflowDefinition inputs are correctly parsed from workflow.yaml."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        definition = workflow._definition

        input_names = [i.name for i in definition.inputs]
        assert "task_a" in input_names
        assert "message" in input_names
        assert "required_input" in input_names

    def test_definition_inputs_defaults(self, mock_declarative_workflow_repo):
        """Optional inputs have their defaults loaded."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        message_input = next(i for i in workflow._definition.inputs if i.name == "message")
        assert message_input.default == "hello"
        assert message_input.required is False

    def test_definition_required_input(self, mock_declarative_workflow_repo):
        """Required inputs are marked as such."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        required = next(i for i in workflow._definition.inputs if i.name == "required_input")
        assert required.required is True

    def test_definition_steps_loaded(self, mock_declarative_workflow_repo):
        """Steps are correctly parsed from workflow.yaml."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        steps = workflow._definition.steps

        assert len(steps) == 2
        assert steps[0].id == "step-a"
        assert steps[1].id == "step-b"

    def test_step_uses_expression(self, mock_declarative_workflow_repo):
        """Step uses: can be a ${{ }} expression."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        step_a = workflow._definition.steps[0]
        assert step_a.uses == "${{ inputs.task_a }}"

    def test_step_needs(self, mock_declarative_workflow_repo):
        """Step needs: list is correctly parsed."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        step_b = workflow._definition.steps[1]
        assert step_b.needs == ["step-a"]

    def test_step_with_block(self, mock_declarative_workflow_repo):
        """Step with: block is correctly parsed."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        step_b = workflow._definition.steps[1]
        assert step_b.with_["data"] == "${{ steps.step-a.outputs.result }}"

    def test_has_create_workflow_method(self, mock_declarative_workflow_repo):
        """DeclarativeWorkflow exposes create_workflow."""
        workflow = AutoWorkflow.from_repo(mock_declarative_workflow_repo)
        assert hasattr(workflow, "create_workflow")
        assert callable(workflow.create_workflow)

    def test_prefers_workflow_yaml_over_ix_py(self, tmp_path):
        """If both workflow.yaml and ix.py exist, workflow.yaml takes precedence."""
        repo = tmp_path / "mixed-repo"
        repo.mkdir()
        (repo / "workflow.yaml").write_text(
            "repo_type: workflow\ntype: mixed\nsteps:\n  - id: s\n    uses: local/t\n"
        )
        (repo / "ix.py").write_text(
            "from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig\n"
            "class _C(BaseWorkflowConfig):\n    type: str = 'mixed'\n"
            "class AWorkflow(BaseWorkflow):\n    config_class = _C\n"
            "    def create_workflow(self, job, **kw): pass\n"
        )

        workflow = AutoWorkflow.from_repo(str(repo))
        assert isinstance(workflow, DeclarativeWorkflow)

    def test_directory_without_workflow_yaml_uses_ix_py(self, mock_workflow_repo):
        """Repository without workflow.yaml falls back to ix.py (BaseWorkflow subclass)."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)
        assert not isinstance(workflow, DeclarativeWorkflow)
        assert isinstance(workflow, BaseWorkflow)


@pytest.mark.integration
class TestWorkflowDefinitionFromYaml:
    """Unit-level tests for WorkflowDefinition.from_yaml()."""

    def test_from_yaml_parses_correctly(self, mock_declarative_workflow_repo):
        from pathlib import Path
        definition = WorkflowDefinition.from_yaml(
            mock_declarative_workflow_repo / "workflow.yaml"
        )
        assert definition.type == "test-declarative"
        assert len(definition.steps) == 2

    def test_from_yaml_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            WorkflowDefinition.from_yaml(tmp_path / "workflow.yaml")

    def test_step_with_alias_parsed(self, mock_declarative_workflow_repo):
        """Step 'with' key is accessible via with_ attribute."""
        definition = WorkflowDefinition.from_yaml(
            mock_declarative_workflow_repo / "workflow.yaml"
        )
        step_a = definition.steps[0]
        assert "message" in step_a.with_
        assert "label" in step_a.with_
