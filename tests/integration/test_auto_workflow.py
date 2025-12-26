"""
Integration tests for AutoWorkflow dynamic loading.
"""

import pytest

from interaxions import AutoWorkflow
from interaxions.workflows.base_workflow import BaseWorkflow
from interaxions.workflows.rollout_and_verify.workflow import RolloutAndVerify


@pytest.mark.integration
class TestAutoWorkflowBuiltin:
    """Tests for loading built-in workflows."""

    def test_load_builtin_rollout_and_verify(self):
        """Test loading the built-in rollout-and-verify workflow."""
        workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        
        assert workflow_template is not None
        assert isinstance(workflow_template, RolloutAndVerify)
        assert isinstance(workflow_template, BaseWorkflow)
        assert workflow_template.config is not None
        assert workflow_template.config.type == "rollout-and-verify"

    def test_load_builtin_with_revision_none(self):
        """Test loading built-in workflow with revision=None."""
        workflow_template = AutoWorkflow.from_repo("rollout-and-verify", revision=None)
        
        assert workflow_template is not None
        assert isinstance(workflow_template, RolloutAndVerify)

    def test_load_builtin_invalid_name(self):
        """Test that loading non-existent workflow raises error."""
        with pytest.raises(Exception):  # Could be ValueError, ImportError, etc.
            AutoWorkflow.from_repo("non-existent-workflow")

    def test_workflow_has_config(self):
        """Test that loaded workflow has valid configuration."""
        workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        
        assert hasattr(workflow_template, "config")
        assert workflow_template.config is not None
        assert hasattr(workflow_template.config, "type")
        assert workflow_template.config.type == "rollout-and-verify"

    def test_workflow_has_create_workflow(self):
        """Test that loaded workflow template has create_workflow method."""
        workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        
        assert hasattr(workflow_template, "create_workflow")
        assert callable(workflow_template.create_workflow)

    def test_workflow_config_optional_templates(self):
        """Test that workflow can be loaded without templates field."""
        workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        
        # rollout-and-verify may or may not have templates
        # The important thing is it loads successfully
        assert workflow_template.config is not None
        assert hasattr(workflow_template.config, "templates")


@pytest.mark.integration
class TestAutoWorkflowFromPath:
    """Tests for loading workflows from local paths."""

    def test_load_from_absolute_path(self, project_root):
        """Test loading workflow from absolute path (external repo)."""
        workflow_path = project_root / "tests" / "fixtures" / "mock_repos" / "test-workflow"
        
        workflow_template = AutoWorkflow.from_repo(str(workflow_path))
        
        assert workflow_template is not None
        assert isinstance(workflow_template, BaseWorkflow)

    def test_load_from_path_object(self, project_root):
        """Test loading workflow from Path object (external repo)."""
        from pathlib import Path
        
        workflow_path = Path(project_root) / "tests" / "fixtures" / "mock_repos" / "test-workflow"
        
        workflow_template = AutoWorkflow.from_repo(workflow_path)
        
        assert workflow_template is not None
        assert isinstance(workflow_template, BaseWorkflow)


@pytest.mark.integration
class TestAutoWorkflowTemplates:
    """Tests for workflow template loading."""

    def test_load_workflow_config_with_templates(self, project_root):
        """Test loading workflow config with templates from fixtures."""
        from pathlib import Path
        from interaxions.workflows.base_workflow import BaseWorkflowConfig
        
        workflow_path = Path(project_root) / "tests" / "fixtures" / "mock_repos" / "test-workflow"
        
        # Load config directly (bypasses AutoWorkflow hub loading)
        config_dict = BaseWorkflowConfig._load_config_dict(workflow_path)
        
        # Should have templates field with file paths
        assert "templates" in config_dict
        assert isinstance(config_dict["templates"], dict)
        assert "main" in config_dict["templates"]
        assert "verification" in config_dict["templates"]
        
        # Load templates
        config_dict = BaseWorkflowConfig._load_templates(config_dict, workflow_path)
        
        # Templates should now be loaded as strings
        assert isinstance(config_dict["templates"]["main"], str)
        assert isinstance(config_dict["templates"]["verification"], str)
        
        # Templates should contain expected content
        assert "Running main workflow" in config_dict["templates"]["main"]
        assert "Running verification" in config_dict["templates"]["verification"]
        assert "{{ environment_id }}" in config_dict["templates"]["main"]
        assert "{{ status }}" in config_dict["templates"]["verification"]


@pytest.mark.integration
class TestWorkflowInterface:
    """Tests for workflow interface compliance."""

    def test_workflow_interface_compliance(self):
        """Test that loaded workflow complies with BaseWorkflow interface."""
        workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        
        # Must have these methods/attributes
        assert hasattr(workflow_template, "config")
        assert hasattr(workflow_template, "create_workflow")
        assert hasattr(workflow_template, "from_repo")

    def test_workflow_type_inference(self):
        """Test that return type is BaseWorkflow."""
        workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
        
        # Should be a BaseWorkflow instance
        assert isinstance(workflow_template, BaseWorkflow)
        
        # Should also be the concrete type
        assert isinstance(workflow_template, RolloutAndVerify)

