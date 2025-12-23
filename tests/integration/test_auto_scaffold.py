"""
Integration tests for AutoScaffold dynamic loading.
"""

import pytest

from interaxions import AutoScaffold
from interaxions.scaffolds.base_scaffold import BaseScaffold
from interaxions.scaffolds.swe_agent.agent import SWEAgent


@pytest.mark.integration
class TestAutoScaffoldBuiltin:
    """Tests for loading built-in scaffolds."""

    def test_load_builtin_swe_agent(self):
        """Test loading the built-in swe-agent scaffold."""
        scaffold = AutoScaffold.from_repo("swe-agent")
        
        assert scaffold is not None
        assert isinstance(scaffold, SWEAgent)
        assert isinstance(scaffold, BaseScaffold)
        assert scaffold.config is not None
        assert scaffold.config.type == "swe-agent"

    def test_load_builtin_with_revision_none(self):
        """Test loading built-in scaffold with revision=None."""
        scaffold = AutoScaffold.from_repo("swe-agent", revision=None)
        
        assert scaffold is not None
        assert isinstance(scaffold, SWEAgent)

    def test_load_builtin_invalid_name(self):
        """Test that loading non-existent scaffold raises error."""
        with pytest.raises(Exception):  # Could be ValueError, ImportError, etc.
            AutoScaffold.from_repo("non-existent-scaffold")

    def test_scaffold_has_config(self):
        """Test that loaded scaffold has valid configuration."""
        scaffold = AutoScaffold.from_repo("swe-agent")
        
        assert hasattr(scaffold, "config")
        assert scaffold.config is not None
        assert hasattr(scaffold.config, "type")
        assert scaffold.config.type == "swe-agent"

    def test_scaffold_has_create_task(self):
        """Test that loaded scaffold has create_task method."""
        scaffold = AutoScaffold.from_repo("swe-agent")
        
        assert hasattr(scaffold, "create_task")
        assert callable(scaffold.create_task)

    def test_scaffold_templates_loaded(self):
        """Test that scaffold templates are loaded."""
        scaffold = AutoScaffold.from_repo("swe-agent")
        
        # SWEAgent should have templates
        assert hasattr(scaffold, "templates")
        assert scaffold.templates is not None
        assert len(scaffold.templates) > 0


@pytest.mark.integration
class TestAutoScaffoldFromPath:
    """Tests for loading scaffolds from local paths."""

    def test_load_from_absolute_path(self, project_root):
        """Test loading scaffold from absolute path."""
        scaffold_path = project_root / "interaxions" / "scaffolds" / "swe_agent"
        
        scaffold = AutoScaffold.from_repo(str(scaffold_path))
        
        assert scaffold is not None
        assert isinstance(scaffold, BaseScaffold)

    def test_load_from_path_object(self, project_root):
        """Test loading scaffold from Path object."""
        from pathlib import Path
        
        scaffold_path = Path(project_root) / "interaxions" / "scaffolds" / "swe_agent"
        
        scaffold = AutoScaffold.from_repo(scaffold_path)
        
        assert scaffold is not None
        assert isinstance(scaffold, BaseScaffold)


@pytest.mark.integration
class TestAutoScaffoldTypeInference:
    """Tests for type inference with AutoScaffold."""

    def test_return_type_is_base_scaffold(self):
        """Test that return type is BaseScaffold."""
        scaffold = AutoScaffold.from_repo("swe-agent")
        
        # Should be a BaseScaffold instance
        assert isinstance(scaffold, BaseScaffold)
        
        # Should also be the concrete type
        assert isinstance(scaffold, SWEAgent)

    def test_scaffold_interface_compliance(self):
        """Test that loaded scaffold complies with BaseScaffold interface."""
        scaffold = AutoScaffold.from_repo("swe-agent")
        
        # Must have these methods/attributes
        assert hasattr(scaffold, "config")
        assert hasattr(scaffold, "templates")
        assert hasattr(scaffold, "create_task")
        assert hasattr(scaffold, "from_repo")

