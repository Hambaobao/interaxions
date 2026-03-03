"""
Integration tests for AutoWorkflow dynamic loading from local repositories.

All tests use the test-workflow mock repo in tests/fixtures/mock_repos/.
Built-in workflows have been removed; all components are loaded from
external repositories via local paths or remote Git URLs.
"""

import pytest

from interaxions import AutoWorkflow
from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig


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
