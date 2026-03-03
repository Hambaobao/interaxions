"""
Integration tests for AutoScaffold dynamic loading from local repositories.

All tests use the test-scaffold mock repo in tests/fixtures/mock_repos/.
Built-in scaffolds have been removed; all components are now loaded from
external repositories via local paths or remote Git URLs.
"""

import pytest

from interaxions import AutoScaffold
from interaxions.scaffolds.base_scaffold import BaseScaffold, BaseScaffoldConfig


@pytest.mark.integration
class TestAutoScaffoldFromLocalPath:
    """Tests for loading a scaffold from a local path."""

    def test_load_from_string_path(self, mock_scaffold_repo):
        """AutoScaffold.from_repo() accepts a string path."""
        scaffold = AutoScaffold.from_repo(str(mock_scaffold_repo))

        assert scaffold is not None
        assert isinstance(scaffold, BaseScaffold)

    def test_load_from_path_object(self, mock_scaffold_repo):
        """AutoScaffold.from_repo() accepts a Path object."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)

        assert scaffold is not None
        assert isinstance(scaffold, BaseScaffold)

    def test_scaffold_has_config(self, mock_scaffold_repo):
        """Loaded scaffold exposes a populated config attribute."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)

        assert hasattr(scaffold, "config")
        assert scaffold.config is not None
        assert isinstance(scaffold.config, BaseScaffoldConfig)

    def test_config_type_matches_yaml(self, mock_scaffold_repo):
        """Config type field matches the value in config.yaml."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)

        assert scaffold.config.type == "test-scaffold"

    def test_config_custom_fields_loaded(self, mock_scaffold_repo):
        """Config fields defined in config.yaml are accessible."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)

        assert hasattr(scaffold.config, "test_param")
        assert scaffold.config.test_param == "test_value"
        assert scaffold.config.max_iterations == 5

    def test_has_create_task_method(self, mock_scaffold_repo):
        """Scaffold has callable create_task method."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)

        assert hasattr(scaffold, "create_task")
        assert callable(scaffold.create_task)

    def test_has_from_repo_class_method(self, mock_scaffold_repo):
        """Scaffold class exposes from_repo class method."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)

        assert hasattr(scaffold, "from_repo")
        assert callable(scaffold.from_repo)


@pytest.mark.integration
class TestAutoScaffoldDiscovery:
    """Tests for the automatic class discovery in ix.py."""

    def test_discovers_correct_class(self, mock_scaffold_repo):
        """AutoScaffold discovers the single BaseScaffold subclass in ix.py."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)

        # The concrete class should be TestScaffold from the mock repo
        assert type(scaffold).__name__ == "TestScaffold"

    def test_invalid_path_raises(self, tmp_path):
        """Loading from a path with no config.yaml raises FileNotFoundError."""
        empty_dir = tmp_path / "empty-scaffold"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            AutoScaffold.from_repo(str(empty_dir))

    def test_path_to_file_raises(self, mock_scaffold_repo):
        """Passing a file path (not a directory) raises an error."""
        ix_file = mock_scaffold_repo / "ix.py"
        assert ix_file.exists()

        with pytest.raises(Exception):
            AutoScaffold.from_repo(str(ix_file))

    def test_no_base_class_subclass_raises(self, tmp_path):
        """Repository without a BaseScaffold subclass raises ValueError."""
        repo = tmp_path / "bad-scaffold"
        repo.mkdir()
        (repo / "config.yaml").write_text("repo_type: scaffold\ntype: bad\n")
        (repo / "ix.py").write_text("# no classes here\n")

        with pytest.raises(ValueError, match="No class inheriting from BaseScaffold"):
            AutoScaffold.from_repo(str(repo))


@pytest.mark.integration
class TestBaseScaffoldConfig:
    """Tests for BaseScaffoldConfig.from_repo() loading logic."""

    def test_loads_config_from_yaml(self, mock_scaffold_repo):
        """BaseScaffoldConfig.from_repo() reads config.yaml correctly."""
        config = BaseScaffoldConfig.from_repo(mock_scaffold_repo)

        assert config is not None
        assert config.repo_type == "scaffold"

    def test_missing_config_raises(self, tmp_path):
        """from_repo raises FileNotFoundError when config.yaml is missing."""
        empty = tmp_path / "no-config"
        empty.mkdir()

        with pytest.raises(FileNotFoundError):
            BaseScaffoldConfig.from_repo(empty)

    def test_template_loading(self, tmp_path):
        """Templates listed in config.yaml are loaded as strings."""
        repo = tmp_path / "scaffold-with-templates"
        repo.mkdir()
        templates_dir = repo / "templates"
        templates_dir.mkdir()
        (templates_dir / "main.j2").write_text("Hello {{ name }}!")

        (repo / "config.yaml").write_text(
            "repo_type: scaffold\ntype: test\ntemplates:\n  main: templates/main.j2\n"
        )

        from interaxions.scaffolds.base_scaffold import BaseScaffoldConfig as BSC

        class _Cfg(BSC):
            type: str
            templates: dict = {}

        config = _Cfg.from_repo(repo)
        assert "main" in config.templates
        assert "Hello" in config.templates["main"]

    def test_missing_template_file_raises(self, tmp_path):
        """References to a nonexistent template file raise FileNotFoundError."""
        repo = tmp_path / "bad-templates"
        repo.mkdir()
        (repo / "config.yaml").write_text(
            "repo_type: scaffold\ntype: test\ntemplates:\n  main: templates/missing.j2\n"
        )

        with pytest.raises(FileNotFoundError):
            BaseScaffoldConfig.from_repo(repo)
