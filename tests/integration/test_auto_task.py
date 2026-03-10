"""
Integration tests for AutoTask dynamic loading from local repositories.

All tests use the test-task mock repo in tests/fixtures/mock_repos/.
"""

import pytest

from interaxions.hub import AutoTask
from interaxions.tasks.base_task import BaseTask, BaseTaskConfig


@pytest.mark.integration
class TestAutoTaskFromLocalPath:
    """Tests for loading a task from a local path."""

    def test_load_from_string_path(self, mock_task_repo):
        """AutoTask.from_repo() accepts a string path."""
        task = AutoTask.from_repo(str(mock_task_repo))

        assert task is not None
        assert isinstance(task, BaseTask)

    def test_load_from_path_object(self, mock_task_repo):
        """AutoTask.from_repo() accepts a Path object."""
        task = AutoTask.from_repo(mock_task_repo)

        assert task is not None
        assert isinstance(task, BaseTask)

    def test_has_config(self, mock_task_repo):
        """Loaded task exposes a populated config attribute."""
        task = AutoTask.from_repo(mock_task_repo)

        assert hasattr(task, "config")
        assert task.config is not None
        assert isinstance(task.config, BaseTaskConfig)

    def test_config_type_matches_yaml(self, mock_task_repo):
        """Config type field matches the value in config.yaml."""
        task = AutoTask.from_repo(mock_task_repo)

        assert task.config.type == "test-task"

    def test_config_custom_fields_loaded(self, mock_task_repo):
        """Config fields defined in config.yaml are accessible."""
        task = AutoTask.from_repo(mock_task_repo)

        assert hasattr(task.config, "image")
        assert task.config.image == "ghcr.io/ix-hub/test-task:latest"
        assert task.config.command == "python run.py"

    def test_has_create_task_method(self, mock_task_repo):
        """Task has callable create_task method."""
        task = AutoTask.from_repo(mock_task_repo)

        assert hasattr(task, "create_task")
        assert callable(task.create_task)

    def test_has_from_repo_class_method(self, mock_task_repo):
        """Task class exposes from_repo class method."""
        task = AutoTask.from_repo(mock_task_repo)

        assert hasattr(task, "from_repo")
        assert callable(task.from_repo)

    def test_has_render_template_method(self, mock_task_repo):
        """Task exposes render_template inherited from BaseRepo."""
        task = AutoTask.from_repo(mock_task_repo)

        assert hasattr(task, "render_template")
        assert callable(task.render_template)


@pytest.mark.integration
class TestAutoTaskDiscovery:
    """Tests for the automatic class discovery in ix.py."""

    def test_discovers_correct_class(self, mock_task_repo):
        """AutoTask discovers the single BaseTask subclass in ix.py."""
        task = AutoTask.from_repo(mock_task_repo)

        assert type(task).__name__ == "TestTask"

    def test_invalid_path_raises(self, tmp_path):
        """Loading from a path with no config.yaml raises FileNotFoundError."""
        empty_dir = tmp_path / "empty-task"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            AutoTask.from_repo(str(empty_dir))

    def test_path_to_file_raises(self, mock_task_repo):
        """Passing a file path (not a directory) raises an error."""
        ix_file = mock_task_repo / "ix.py"
        assert ix_file.exists()

        with pytest.raises(Exception):
            AutoTask.from_repo(str(ix_file))

    def test_no_base_class_subclass_raises(self, tmp_path):
        """Repository without a BaseTask subclass raises ValueError."""
        repo = tmp_path / "bad-task"
        repo.mkdir()
        (repo / "config.yaml").write_text("repo_type: task\ntype: bad\n")
        (repo / "ix.py").write_text("# no classes here\n")

        with pytest.raises(ValueError, match="No class inheriting from BaseTask"):
            AutoTask.from_repo(str(repo))


@pytest.mark.integration
class TestBaseTaskConfig:
    """Tests for BaseTaskConfig.from_repo() loading logic."""

    def test_loads_config_from_yaml(self, mock_task_repo):
        """BaseTaskConfig.from_repo() reads config.yaml correctly."""
        config = BaseTaskConfig.from_repo(mock_task_repo)

        assert config is not None
        assert config.repo_type == "task"

    def test_missing_config_raises(self, tmp_path):
        """from_repo raises FileNotFoundError when config.yaml is missing."""
        empty = tmp_path / "no-config"
        empty.mkdir()

        with pytest.raises(FileNotFoundError):
            BaseTaskConfig.from_repo(empty)

    def test_template_loading(self, tmp_path):
        """Templates listed in config.yaml are loaded as strings."""
        repo = tmp_path / "task-with-templates"
        repo.mkdir()
        templates_dir = repo / "templates"
        templates_dir.mkdir()
        (templates_dir / "run.j2").write_text("python run.py --input {{ input }}")

        (repo / "config.yaml").write_text(
            "repo_type: task\ntype: test\ntemplates:\n  run: templates/run.j2\n"
        )

        from interaxions.tasks.base_task import BaseTaskConfig as BTC
        from typing import Dict
        from pydantic import Field as F

        class _Cfg(BTC):
            type: str
            templates: dict = {}

        config = _Cfg.from_repo(repo)
        assert "run" in config.templates
        assert "python run.py" in config.templates["run"]

    def test_missing_template_file_raises(self, tmp_path):
        """References to a nonexistent template file raise FileNotFoundError."""
        repo = tmp_path / "bad-templates"
        repo.mkdir()
        (repo / "config.yaml").write_text(
            "repo_type: task\ntype: test\ntemplates:\n  run: templates/missing.j2\n"
        )

        with pytest.raises(FileNotFoundError):
            BaseTaskConfig.from_repo(repo)

