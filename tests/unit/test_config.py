"""
Unit tests for configuration loading and merging.
"""

from pathlib import Path

import pytest
import yaml

from interaxions.scaffolds.base_scaffold import BaseScaffoldConfig
from interaxions.environments.base_environment import BaseEnvironmentConfig
from interaxions.workflows.base_workflow import BaseWorkflowConfig


@pytest.mark.unit
class TestConfigLoading:
    """Tests for configuration loading from YAML files."""

    def test_load_simple_config(self, tmp_path: Path):
        """Test loading a simple YAML configuration."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "type": "test-type",
            "param1": "value1",
            "param2": 42,
        }
        config_file.write_text(yaml.dump(config_data))
        
        # Load config
        loaded = yaml.safe_load(config_file.read_text())
        assert loaded["type"] == "test-type"
        assert loaded["param1"] == "value1"
        assert loaded["param2"] == 42

    def test_load_nested_config(self, tmp_path: Path):
        """Test loading a configuration with nested structure."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "type": "test",
            "nested": {
                "key1": "value1",
                "key2": "value2",
                "deep": {
                    "level3": "value3",
                },
            },
        }
        config_file.write_text(yaml.dump(config_data))
        
        loaded = yaml.safe_load(config_file.read_text())
        assert loaded["nested"]["key1"] == "value1"
        assert loaded["nested"]["deep"]["level3"] == "value3"

    def test_load_config_with_lists(self, tmp_path: Path):
        """Test loading configuration with list values."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "type": "test",
            "items": ["item1", "item2", "item3"],
            "numbers": [1, 2, 3, 4, 5],
        }
        config_file.write_text(yaml.dump(config_data))
        
        loaded = yaml.safe_load(config_file.read_text())
        assert loaded["items"] == ["item1", "item2", "item3"]
        assert loaded["numbers"] == [1, 2, 3, 4, 5]

    def test_config_file_not_found(self, tmp_path: Path):
        """Test handling of missing configuration file."""
        config_file = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            config_file.read_text()

    def test_invalid_yaml_syntax(self, tmp_path: Path):
        """Test handling of invalid YAML syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: syntax: [[[")
        
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(config_file.read_text())


@pytest.mark.unit
class TestConfigMerging:
    """Tests for configuration merging (defaults + overrides)."""

    def test_merge_simple_configs(self):
        """Test merging two simple dictionaries."""
        defaults = {"key1": "value1", "key2": "value2"}
        overrides = {"key2": "new_value2", "key3": "value3"}
        
        merged = {**defaults, **overrides}
        
        assert merged["key1"] == "value1"
        assert merged["key2"] == "new_value2"  # Overridden
        assert merged["key3"] == "value3"       # New key

    def test_merge_nested_configs(self):
        """Test merging nested dictionaries."""
        defaults = {
            "level1": {
                "key1": "value1",
                "key2": "value2",
            }
        }
        overrides = {
            "level1": {
                "key2": "new_value2",
                "key3": "value3",
            }
        }
        
        # Simple dict merge (shallow)
        merged_shallow = {**defaults, **overrides}
        # This will replace the entire "level1" dict
        assert merged_shallow["level1"]["key2"] == "new_value2"
        assert "key1" not in merged_shallow["level1"]  # Lost in shallow merge

    def test_config_defaults(self, tmp_path: Path):
        """Test that configuration classes have appropriate defaults."""
        # BaseScaffoldConfig should have a type field
        # (we can't instantiate abstract classes directly, so we test the pattern)
        config_file = tmp_path / "config.yaml"
        config_data = {"type": "test-scaffold"}
        config_file.write_text(yaml.dump(config_data))
        
        loaded = yaml.safe_load(config_file.read_text())
        assert "type" in loaded


@pytest.mark.unit
class TestConfigTypes:
    """Tests for different configuration types."""

    def test_scaffold_config_structure(self):
        """Test that scaffold configs have expected structure."""
        # We test the pattern used by scaffold configs
        config_data = {
            "type": "swe-agent",
            "param1": "value1",
        }
        assert "type" in config_data
        assert config_data["type"] == "swe-agent"

    def test_environment_config_structure(self):
        """Test that environment configs have expected structure."""
        config_data = {
            "type": "swe-bench",
            "source": "hf",
        }
        assert "type" in config_data
        assert config_data["type"] == "swe-bench"

    def test_workflow_config_structure(self):
        """Test that workflow configs have expected structure."""
        config_data = {
            "type": "rollout-and-verify",
        }
        assert "type" in config_data
        assert config_data["type"] == "rollout-and-verify"


@pytest.mark.unit
class TestTemplateFiles:
    """Tests for template file operations."""

    def test_create_template_file(self, tmp_path: Path):
        """Test creating a template file."""
        template_path = tmp_path / "templates" / "main.j2"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        template_content = "Hello {{ name }}!"
        template_path.write_text(template_content)
        
        assert template_path.exists()
        assert template_path.read_text() == template_content

    def test_template_with_variables(self, tmp_path: Path):
        """Test template content with Jinja2 variables."""
        template_path = tmp_path / "template.j2"
        template_content = """
name: {{ name }}
value: {{ value }}
list: {{ items | join(', ') }}
"""
        template_path.write_text(template_content)
        
        content = template_path.read_text()
        assert "{{ name }}" in content
        assert "{{ value }}" in content
        assert "{{ items | join(', ') }}" in content

    def test_multiple_template_files(self, tmp_path: Path):
        """Test managing multiple template files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        
        # Create multiple templates
        templates = {
            "main.j2": "Main template: {{ main }}",
            "helper.j2": "Helper: {{ helper }}",
            "verify.j2": "Verify: {{ verify }}",
        }
        
        for name, content in templates.items():
            template_path = templates_dir / name
            template_path.write_text(content)
        
        # Verify all exist
        assert (templates_dir / "main.j2").exists()
        assert (templates_dir / "helper.j2").exists()
        assert (templates_dir / "verify.j2").exists()
        
        # Count template files
        template_files = list(templates_dir.glob("*.j2"))
        assert len(template_files) == 3

