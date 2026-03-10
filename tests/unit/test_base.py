"""
Unit tests for interaxions/base.py — BaseRepoConfig and BaseRepo.

These tests exercise the shared loading and rendering logic directly,
covering the error branches that integration tests (which use happy-path
mock repos) leave uncovered.
"""

from pathlib import Path
from typing import Any, Dict, Literal, Optional

import pytest
import yaml

from pydantic import Field

from interaxions.base import BaseRepo, BaseRepoConfig


# ---------------------------------------------------------------------------
# Helpers: minimal concrete subclasses for testing
# ---------------------------------------------------------------------------


class _SimpleConfig(BaseRepoConfig):
    """Minimal config with no extra required fields."""
    repo_type: Literal["task"] = "task"


class _ConfigWithTemplates(BaseRepoConfig):
    """Config that declares an optional templates dict."""
    repo_type: Literal["task"] = "task"
    templates: Optional[Dict[str, str]] = Field(default=None)


class _ConcreteRepo(BaseRepo):
    """Minimal concrete BaseRepo for testing render_template."""
    config_class = _ConfigWithTemplates
    config: _ConfigWithTemplates

    def create_task(self, **kwargs: Any) -> None:  # type: ignore[override]
        pass


# ---------------------------------------------------------------------------
# BaseRepoConfig._load_config_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadConfigDict:
    """Tests for BaseRepoConfig._load_config_dict."""

    def test_loads_config_yaml(self, tmp_path: Path):
        """Reads config.yaml and returns a dict."""
        (tmp_path / "config.yaml").write_text("repo_type: task\n")
        result = _SimpleConfig._load_config_dict(tmp_path)
        assert isinstance(result, dict)
        assert result["repo_type"] == "task"

    def test_falls_back_to_config_yml(self, tmp_path: Path):
        """Falls back to config.yml when config.yaml is absent."""
        (tmp_path / "config.yml").write_text("repo_type: task\n")
        result = _SimpleConfig._load_config_dict(tmp_path)
        assert result["repo_type"] == "task"

    def test_prefers_config_yaml_over_yml(self, tmp_path: Path):
        """Prefers config.yaml over config.yml when both exist."""
        (tmp_path / "config.yaml").write_text("source: yaml\nrepo_type: task\n")
        (tmp_path / "config.yml").write_text("source: yml\nrepo_type: task\n")
        result = _SimpleConfig._load_config_dict(tmp_path)
        assert result["source"] == "yaml"

    def test_raises_if_no_config_file(self, tmp_path: Path):
        """Raises FileNotFoundError when neither config.yaml nor config.yml exists."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            _SimpleConfig._load_config_dict(tmp_path)

    def test_raises_if_config_is_not_a_dict(self, tmp_path: Path):
        """Raises ValueError when the YAML root is not a mapping (e.g. a list)."""
        (tmp_path / "config.yaml").write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="Expected a YAML mapping"):
            _SimpleConfig._load_config_dict(tmp_path)

    def test_raises_if_config_is_null(self, tmp_path: Path):
        """Raises ValueError when the YAML file is empty / null."""
        (tmp_path / "config.yaml").write_text("null\n")
        with pytest.raises(ValueError, match="Expected a YAML mapping"):
            _SimpleConfig._load_config_dict(tmp_path)


# ---------------------------------------------------------------------------
# BaseRepoConfig._load_templates
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadTemplates:
    """Tests for BaseRepoConfig._load_templates."""

    def test_no_templates_key_returns_unchanged(self, tmp_path: Path):
        """Config without a 'templates' key is returned as-is."""
        config_dict: Dict[str, Any] = {"repo_type": "task"}
        result = _SimpleConfig._load_templates(config_dict, tmp_path)
        assert result == {"repo_type": "task"}

    def test_templates_not_a_dict_returns_unchanged(self, tmp_path: Path):
        """Config with templates as a non-dict value is returned unchanged."""
        config_dict: Dict[str, Any] = {"repo_type": "task", "templates": "not-a-dict"}
        result = _SimpleConfig._load_templates(config_dict, tmp_path)
        assert result["templates"] == "not-a-dict"

    def test_loads_template_file_content(self, tmp_path: Path):
        """File paths in templates are replaced by their content."""
        (tmp_path / "main.j2").write_text("Hello {{ name }}!")
        config_dict: Dict[str, Any] = {"templates": {"main": "main.j2"}}
        result = _SimpleConfig._load_templates(config_dict, tmp_path)
        assert result["templates"]["main"] == "Hello {{ name }}!"

    def test_raises_if_template_value_not_string(self, tmp_path: Path):
        """Raises ValueError when a template value is not a string path."""
        config_dict: Dict[str, Any] = {"templates": {"main": 42}}
        with pytest.raises(ValueError, match="must be a file path string"):
            _SimpleConfig._load_templates(config_dict, tmp_path)

    def test_raises_if_template_file_missing(self, tmp_path: Path):
        """Raises FileNotFoundError when a referenced template file does not exist."""
        config_dict: Dict[str, Any] = {"templates": {"main": "nonexistent.j2"}}
        with pytest.raises(FileNotFoundError, match="Template file not found"):
            _SimpleConfig._load_templates(config_dict, tmp_path)

    def test_loads_multiple_templates(self, tmp_path: Path):
        """All template entries are loaded correctly."""
        (tmp_path / "a.j2").write_text("AAA")
        (tmp_path / "b.j2").write_text("BBB")
        config_dict: Dict[str, Any] = {"templates": {"a": "a.j2", "b": "b.j2"}}
        result = _SimpleConfig._load_templates(config_dict, tmp_path)
        assert result["templates"]["a"] == "AAA"
        assert result["templates"]["b"] == "BBB"


# ---------------------------------------------------------------------------
# BaseRepoConfig.from_repo
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBaseRepoConfigFromRepo:
    """Tests for BaseRepoConfig.from_repo (directory validation + full pipeline)."""

    def test_raises_if_path_does_not_exist(self, tmp_path: Path):
        """Raises FileNotFoundError when the directory does not exist."""
        with pytest.raises(FileNotFoundError, match="Directory not found"):
            _SimpleConfig.from_repo(tmp_path / "no-such-dir")

    def test_raises_if_path_is_a_file(self, tmp_path: Path):
        """Raises ValueError when the path points to a file, not a directory."""
        f = tmp_path / "config.yaml"
        f.write_text("repo_type: task\n")
        with pytest.raises(ValueError, match="must be a directory"):
            _SimpleConfig.from_repo(f)

    def test_returns_instance_of_calling_class(self, tmp_path: Path):
        """from_repo returns an instance of the concrete config subclass."""
        (tmp_path / "config.yaml").write_text("repo_type: task\n")
        cfg = _SimpleConfig.from_repo(tmp_path)
        assert isinstance(cfg, _SimpleConfig)

    def test_accepts_string_path(self, tmp_path: Path):
        """from_repo accepts a plain string as well as a Path object."""
        (tmp_path / "config.yaml").write_text("repo_type: task\n")
        cfg = _SimpleConfig.from_repo(str(tmp_path))
        assert isinstance(cfg, _SimpleConfig)

    def test_templates_are_inlined(self, tmp_path: Path):
        """Template file paths are replaced by their contents end-to-end."""
        (tmp_path / "tmpl.j2").write_text("Hello {{ x }}!")
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"repo_type": "task", "templates": {"main": "tmpl.j2"}})
        )
        cfg = _ConfigWithTemplates.from_repo(tmp_path)
        assert cfg.templates["main"] == "Hello {{ x }}!"


# ---------------------------------------------------------------------------
# BaseRepo.render_template
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderTemplate:
    """Tests for BaseRepo.render_template."""

    def _make_repo(self, tmp_path: Path, templates: Optional[Dict[str, str]] = None) -> _ConcreteRepo:
        """Helper: build a _ConcreteRepo with optional templates in config."""
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"repo_type": "task"})
        )
        if templates:
            for name, content in templates.items():
                (tmp_path / f"{name}.j2").write_text(content)
            (tmp_path / "config.yaml").write_text(
                yaml.dump({"repo_type": "task", "templates": {n: f"{n}.j2" for n in templates}})
            )
        return _ConcreteRepo.from_repo(tmp_path)

    def test_renders_template_with_context(self, tmp_path: Path):
        """Jinja2 variables are substituted correctly."""
        repo = self._make_repo(tmp_path, {"main": "Hello {{ name }}!"})
        result = repo.render_template("main", {"name": "world"})
        assert result == "Hello world!"

    def test_renders_template_with_multiple_vars(self, tmp_path: Path):
        """Multiple variables are all substituted."""
        repo = self._make_repo(tmp_path, {"script": "{{ a }} + {{ b }} = {{ c }}"})
        result = repo.render_template("script", {"a": "1", "b": "2", "c": "3"})
        assert result == "1 + 2 = 3"

    def test_raises_when_no_templates_in_config(self, tmp_path: Path):
        """Raises ValueError when config has no templates attribute."""
        repo = self._make_repo(tmp_path)  # no templates
        with pytest.raises(ValueError, match="No templates found"):
            repo.render_template("main", {})

    def test_raises_when_template_name_not_found(self, tmp_path: Path):
        """Raises ValueError when the requested template name does not exist."""
        repo = self._make_repo(tmp_path, {"main": "Hello!"})
        with pytest.raises(ValueError, match="not found"):
            repo.render_template("nonexistent", {})

    def test_error_message_includes_available_templates(self, tmp_path: Path):
        """ValueError for missing template lists the available template names."""
        repo = self._make_repo(tmp_path, {"main": "Hello!", "verify": "Verify!"})
        with pytest.raises(ValueError, match="main"):
            repo.render_template("nonexistent", {})

