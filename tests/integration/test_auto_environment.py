"""
Integration tests for AutoEnvironment dynamic loading from local repositories.

All tests use the test-environment mock repo in tests/fixtures/mock_repos/.
The new AutoEnvironment.from_repo() loads a BaseEnvironment executor that
exposes two methods:
  - get(id)           → Environment (pure data object)
  - create_task(...)  → hera Task
"""

import pytest

from interaxions import AutoEnvironment
from interaxions.environments.base_environment import BaseEnvironment, BaseEnvironmentConfig
from interaxions.schemas.task import Environment


@pytest.mark.integration
class TestAutoEnvironmentFromLocalPath:
    """Tests for loading a BaseEnvironment from a local path."""

    def test_load_from_string_path(self, mock_environment_repo):
        """AutoEnvironment.from_repo() accepts a string path."""
        env_task = AutoEnvironment.from_repo(str(mock_environment_repo))

        assert env_task is not None
        assert isinstance(env_task, BaseEnvironment)

    def test_load_from_path_object(self, mock_environment_repo):
        """AutoEnvironment.from_repo() accepts a Path object."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)

        assert env_task is not None
        assert isinstance(env_task, BaseEnvironment)

    def test_has_config(self, mock_environment_repo):
        """Loaded environment executor exposes a populated config."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)

        assert hasattr(env_task, "config")
        assert env_task.config is not None
        assert isinstance(env_task.config, BaseEnvironmentConfig)

    def test_config_type_matches_yaml(self, mock_environment_repo):
        """Config type matches the value in config.yaml."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)

        assert env_task.config.type == "test-environment"

    def test_has_get_method(self, mock_environment_repo):
        """Loaded executor exposes callable get() method."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)

        assert hasattr(env_task, "get")
        assert callable(env_task.get)

    def test_has_create_task_method(self, mock_environment_repo):
        """Loaded executor exposes callable create_task() method."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)

        assert hasattr(env_task, "create_task")
        assert callable(env_task.create_task)


@pytest.mark.integration
class TestEnvironmentGet:
    """Tests for BaseEnvironment.get() returning an Environment data object."""

    def test_get_returns_environment(self, mock_environment_repo):
        """get() returns an Environment instance."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("django__django-12345")

        assert env is not None
        assert isinstance(env, Environment)

    def test_get_preserves_id(self, mock_environment_repo):
        """Returned Environment.id matches the queried id."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("astropy__astropy-12907")

        assert env.id == "astropy__astropy-12907"

    def test_get_type_matches_config(self, mock_environment_repo):
        """Returned Environment.type matches the repo's config type."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("any-instance")

        assert env.type == "test-environment"

    def test_get_data_is_dict(self, mock_environment_repo):
        """Returned Environment.data is a dict."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("test-123")

        assert isinstance(env.data, dict)

    def test_get_data_contains_instance_id(self, mock_environment_repo):
        """Returned Environment.data contains at least the instance_id."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("my-instance-456")

        assert "instance_id" in env.data
        assert env.data["instance_id"] == "my-instance-456"

    def test_get_different_ids(self, mock_environment_repo):
        """Calling get() with different ids returns different Environments."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env1 = env_task.get("instance-1")
        env2 = env_task.get("instance-2")

        assert env1.id != env2.id
        assert env1.data["instance_id"] != env2.data["instance_id"]

    def test_environment_serializable(self, mock_environment_repo):
        """Environment returned by get() is JSON-serializable."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("test-inst")

        json_str = env.model_dump_json()
        assert env.id in json_str

        restored = Environment.model_validate_json(json_str)
        assert restored.id == env.id
        assert restored.data == env.data


@pytest.mark.integration
class TestAutoEnvironmentDiscovery:
    """Tests for the automatic class discovery in ix.py."""

    def test_discovers_correct_class(self, mock_environment_repo):
        """AutoEnvironment discovers the single BaseEnvironment subclass."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        assert type(env_task).__name__ == "TestEnvironment"

    def test_invalid_path_raises(self, tmp_path):
        """Loading from a directory with no config.yaml raises FileNotFoundError."""
        empty = tmp_path / "empty-env"
        empty.mkdir()

        with pytest.raises(FileNotFoundError):
            AutoEnvironment.from_repo(str(empty))

    def test_no_base_class_subclass_raises(self, tmp_path):
        """Repository without a BaseEnvironment subclass raises ValueError."""
        repo = tmp_path / "bad-env"
        repo.mkdir()
        (repo / "config.yaml").write_text("repo_type: environment\ntype: bad\n")
        (repo / "ix.py").write_text("# no classes here\n")

        with pytest.raises(ValueError, match="No class inheriting from BaseEnvironment"):
            AutoEnvironment.from_repo(str(repo))


@pytest.mark.integration
class TestBaseEnvironmentConfig:
    """Tests for BaseEnvironmentConfig loading logic."""

    def test_loads_config_from_yaml(self, mock_environment_repo):
        config = BaseEnvironmentConfig.from_repo(mock_environment_repo)
        assert config.repo_type == "environment"
        assert config.type == "test-environment"

    def test_missing_config_raises(self, tmp_path):
        empty = tmp_path / "no-config"
        empty.mkdir()

        with pytest.raises(FileNotFoundError):
            BaseEnvironmentConfig.from_repo(empty)

    def test_template_loading(self, tmp_path):
        """Templates in config.yaml are loaded from files as strings."""
        repo = tmp_path / "env-with-templates"
        repo.mkdir()
        tmpl_dir = repo / "templates"
        tmpl_dir.mkdir()
        (tmpl_dir / "verify.j2").write_text("Verify {{ instance_id }}")

        (repo / "config.yaml").write_text(
            "repo_type: environment\ntype: test\ntemplates:\n  verify: templates/verify.j2\n"
        )

        from interaxions.environments.base_environment import BaseEnvironmentConfig as BEC

        class _Cfg(BEC):
            type: str
            templates: dict = {}

        config = _Cfg.from_repo(repo)
        assert "verify" in config.templates
        assert "Verify" in config.templates["verify"]

    def test_missing_template_file_raises(self, tmp_path):
        repo = tmp_path / "bad-templates"
        repo.mkdir()
        (repo / "config.yaml").write_text(
            "repo_type: environment\ntype: test\ntemplates:\n  verify: templates/missing.j2\n"
        )

        with pytest.raises(FileNotFoundError):
            BaseEnvironmentConfig.from_repo(repo)
