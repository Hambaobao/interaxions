"""
Integration tests for AutoEnvironment and AutoEnvironmentFactory dynamic loading.
"""

import pytest

from interaxions import AutoEnvironment, AutoEnvironmentFactory
from interaxions.environments.base_environment import BaseEnvironment, BaseEnvironmentFactory
from interaxions.environments.swe_bench.env import SWEBenchEnvironment, SWEBenchFactory


@pytest.mark.integration
class TestAutoEnvironmentFactoryBuiltin:
    """Tests for loading built-in environment factories."""

    def test_load_builtin_swe_bench_factory(self):
        """Test loading the built-in swe-bench environment factory."""
        factory = AutoEnvironmentFactory.from_repo("swe-bench")
        
        assert factory is not None
        assert isinstance(factory, SWEBenchFactory)
        assert isinstance(factory, BaseEnvironmentFactory)
        assert factory.config is not None
        assert factory.config.type == "swe-bench"

    def test_factory_has_config(self):
        """Test that loaded factory has valid configuration."""
        factory = AutoEnvironmentFactory.from_repo("swe-bench")
        
        assert hasattr(factory, "config")
        assert factory.config is not None
        assert hasattr(factory.config, "type")

    def test_factory_has_get_methods(self):
        """Test that factory has get_from_hf and get_from_oss methods."""
        factory = AutoEnvironmentFactory.from_repo("swe-bench")
        
        assert hasattr(factory, "get_from_hf")
        assert callable(factory.get_from_hf)
        assert hasattr(factory, "get_from_oss")
        assert callable(factory.get_from_oss)

    def test_factory_templates_loaded(self):
        """Test that factory templates are loaded."""
        factory = AutoEnvironmentFactory.from_repo("swe-bench")
        
        assert hasattr(factory.config, "templates")
        assert factory.config.templates is not None
        assert len(factory.config.templates) > 0


@pytest.mark.integration
class TestAutoEnvironmentFactoryMethods:
    """Tests for environment factory get_from_* methods."""

    def test_get_from_hf_creates_environment(self, mocker):
        """Test that get_from_hf creates an environment instance."""
        factory = AutoEnvironmentFactory.from_repo("swe-bench")
        
        # Mock the actual HuggingFace loading with proper structure
        mock_dataset = mocker.MagicMock()
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)
        
        mock_load = mocker.patch("datasets.load_dataset")
        mock_load.return_value = mock_dataset
        
        env = factory.get_from_hf(
            environment_id="test-123",
            dataset="test-dataset",
            split="test",
        )
        
        assert env is not None
        assert isinstance(env, BaseEnvironment)
        assert isinstance(env, SWEBenchEnvironment)
        assert env.environment_id == "test-123"

    @pytest.mark.skipif(True, reason="ossdata is optional dependency")
    def test_get_from_oss_creates_environment(self, mocker):
        """Test that get_from_oss creates an environment instance."""
        factory = AutoEnvironmentFactory.from_repo("swe-bench")
        
        # Mock OSS loading with proper structure
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_oss = mocker.patch("ossdata.Dataset.load")
        mock_oss.return_value = [mock_item]
        
        env = factory.get_from_oss(
            environment_id="test-123",
            dataset="test-dataset",
            split="test",
            oss_region="cn-hangzhou",
            oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
            oss_access_key_id="test-key",
            oss_access_key_secret="test-secret",
        )
        
        assert env is not None
        assert isinstance(env, BaseEnvironment)
        assert env.environment_id == "test-123"

    def test_environment_has_create_task(self, mocker):
        """Test that created environment has create_task method."""
        factory = AutoEnvironmentFactory.from_repo("swe-bench")
        
        # Mock with proper structure
        mock_dataset = mocker.MagicMock()
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)
        
        mock_load = mocker.patch("datasets.load_dataset")
        mock_load.return_value = mock_dataset
        
        env = factory.get_from_hf(
            environment_id="test-123",
            dataset="test-dataset",
            split="test",
        )
        
        assert hasattr(env, "create_task")
        assert callable(env.create_task)


@pytest.mark.integration
class TestAutoEnvironmentUnified:
    """Tests for unified AutoEnvironment.from_repo() API."""

    def test_auto_environment_from_repo_hf(self, mocker):
        """Test AutoEnvironment.from_repo() with HF source."""
        # Mock HuggingFace loading with proper structure
        mock_dataset = mocker.MagicMock()
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)
        
        mock_load = mocker.patch("datasets.load_dataset")
        mock_load.return_value = mock_dataset
        
        env = AutoEnvironment.from_repo(
            repo_name_or_path="swe-bench",
            environment_id="test-123",
            source="hf",
            dataset="test-dataset",
            split="test",
        )
        
        assert env is not None
        assert isinstance(env, BaseEnvironment)
        assert env.environment_id == "test-123"

    @pytest.mark.skipif(True, reason="ossdata is optional dependency")
    def test_auto_environment_from_repo_oss(self, mocker):
        """Test AutoEnvironment.from_repo() with OSS source."""
        # Mock OSS loading with proper structure
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_oss = mocker.patch("ossdata.Dataset.load")
        mock_oss.return_value = [mock_item]
        
        env = AutoEnvironment.from_repo(
            repo_name_or_path="swe-bench",
            environment_id="test-123",
            source="oss",
            dataset="test-dataset",
            split="test",
            oss_region="cn-hangzhou",
            oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
            oss_access_key_id="test-key",
            oss_access_key_secret="test-secret",
        )
        
        assert env is not None
        assert isinstance(env, BaseEnvironment)

    def test_auto_environment_unsupported_source(self):
        """Test that unsupported source raises error."""
        with pytest.raises(ValueError) as exc_info:
            AutoEnvironment.from_repo(
                repo_name_or_path="swe-bench",
                environment_id="test-123",
                source="unsupported-source",
            )
        assert "unsupported" in str(exc_info.value).lower()

    def test_auto_environment_with_revision(self, mocker):
        """Test AutoEnvironment with specific revision."""
        # Mock HF loading with proper structure
        mock_dataset = mocker.MagicMock()
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)
        
        mock_load = mocker.patch("datasets.load_dataset")
        mock_load.return_value = mock_dataset
        
        env = AutoEnvironment.from_repo(
            repo_name_or_path="swe-bench",
            environment_id="test-123",
            source="hf",
            revision=None,  # Should use default branch
            dataset="test-dataset",
            split="test",
        )
        
        assert env is not None


@pytest.mark.integration
class TestAutoEnvironmentFromPath:
    """Tests for loading environments from local paths."""

    @pytest.mark.skipif(True, reason="Built-in environments should not be loaded via from_repo - need mock environment repo")
    def test_load_from_absolute_path(self, project_root, mocker):
        """Test loading environment from absolute path (external repo)."""
        # TODO: Create mock_repos/test-environment and update path
        env_path = project_root / "tests" / "fixtures" / "mock_repos" / "test-environment"
        
        # Mock HF loading with proper structure
        mock_dataset = mocker.MagicMock()
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)
        
        mock_load = mocker.patch("datasets.load_dataset")
        mock_load.return_value = mock_dataset
        
        env = AutoEnvironment.from_repo(
            repo_name_or_path=str(env_path),
            environment_id="test-123",
            source="hf",
            dataset="test-dataset",
            split="test",
        )
        
        assert env is not None
        assert isinstance(env, BaseEnvironment)


@pytest.mark.integration
class TestEnvironmentInterface:
    """Tests for environment interface compliance."""

    def test_environment_interface_compliance(self, mocker):
        """Test that loaded environment complies with BaseEnvironment interface."""
        # Mock HF loading with proper structure
        mock_dataset = mocker.MagicMock()
        mock_item = {
            "instance_id": "test-123",
            "repo": "test/repo",
            "base_commit": "abc123",
            "patch": "test patch",
            "test_patch": "test test_patch",
            "problem_statement": "test problem",
            "hints_text": "",
            "created_at": "2024-01-01",
            "version": "1.0",
            "FAIL_TO_PASS": "[]",
            "PASS_TO_PASS": "[]",
            "environment_setup_commit": "abc123",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)
        
        mock_load = mocker.patch("datasets.load_dataset")
        mock_load.return_value = mock_dataset
        
        env = AutoEnvironment.from_repo(
            repo_name_or_path="swe-bench",
            environment_id="test-123",
            source="hf",
            dataset="test-dataset",
            split="test",
        )
        
        # Must have these attributes/methods
        assert hasattr(env, "environment_id")
        assert hasattr(env, "create_task")
        assert callable(env.create_task)
        assert env.environment_id == "test-123"

