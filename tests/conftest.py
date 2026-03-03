"""
Pytest configuration and shared fixtures for all tests.
"""

from pathlib import Path

import pytest

from interaxions.schemas import (
    EnvironmentConfig,
    RuntimeConfig,
    ScaffoldConfig,
    WorkflowConfig,
    XJob,
)


# ============================================================================
# Path Fixtures
# ============================================================================


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def tests_dir(project_root: Path) -> Path:
    """Return the tests directory."""
    return project_root / "tests"


@pytest.fixture
def fixtures_dir(tests_dir: Path) -> Path:
    """Return the fixtures directory."""
    return tests_dir / "fixtures"


@pytest.fixture
def mock_repos_dir(fixtures_dir: Path) -> Path:
    """Return the mock repositories directory."""
    return fixtures_dir / "mock_repos"


@pytest.fixture
def mock_scaffold_repo(mock_repos_dir: Path) -> Path:
    """Return the test-scaffold mock repo path."""
    return mock_repos_dir / "test-scaffold"


@pytest.fixture
def mock_workflow_repo(mock_repos_dir: Path) -> Path:
    """Return the test-workflow mock repo path."""
    return mock_repos_dir / "test-workflow"


@pytest.fixture
def mock_environment_repo(mock_repos_dir: Path) -> Path:
    """Return the test-environment mock repo path."""
    return mock_repos_dir / "test-environment"


# ============================================================================
# Schema Fixtures
# ============================================================================


@pytest.fixture
def sample_scaffold_config() -> ScaffoldConfig:
    """Return a sample ScaffoldConfig."""
    return ScaffoldConfig(
        repo_name_or_path="ix-hub/swe-agent",
        revision="v1.0.0",
        params={
            "sweagent_config": "default.yaml",
            "tools_parse_function": "function_calling",
            "max_iterations": 50,
        },
    )


@pytest.fixture
def sample_environment_config() -> EnvironmentConfig:
    """Return a sample EnvironmentConfig."""
    return EnvironmentConfig(
        repo_name_or_path="ix-hub/swe-bench",
        revision="v2.0.0",
        id="astropy__astropy-12907",
        params={
            "predictions_path": "/tmp/output/predictions.jsonl",
        },
    )


@pytest.fixture
def sample_workflow_config(
    sample_scaffold_config: ScaffoldConfig,
    sample_environment_config: EnvironmentConfig,
) -> WorkflowConfig:
    """Return a sample WorkflowConfig with scaffold, environment, and model in params."""
    return WorkflowConfig(
        repo_name_or_path="ix-hub/swe-rollout-verify",
        revision="v1.0.0",
        params={
            "scaffold": sample_scaffold_config.model_dump(),
            "environment": sample_environment_config.model_dump(),
            "model": {
                "type": "litellm",
                "provider": "openai",
                "model": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
            },
        },
    )


@pytest.fixture
def sample_runtime_config() -> RuntimeConfig:
    """Return a sample RuntimeConfig."""
    return RuntimeConfig(
        namespace="experiments",
        service_account="argo-workflow",
        image_pull_policy="IfNotPresent",
        ttl_seconds_after_finished=3600,
        extra_params={
            "labels": {"project": "interaxions", "team": "research"},
            "annotations": {"description": "Test workflow"},
            "node_selector": {"gpu": "true"},
        },
    )


@pytest.fixture
def sample_job(
    sample_workflow_config: WorkflowConfig,
    sample_runtime_config: RuntimeConfig,
) -> XJob:
    """Return a complete sample XJob."""
    return XJob(
        name="test-swe-bench-job",
        description="A test SWE-bench job for unit testing",
        tags=["test", "swe-bench", "unit"],
        labels={"team": "research", "priority": "high"},
        workflow=sample_workflow_config,
        runtime=sample_runtime_config,
    )


@pytest.fixture
def sample_job_dict() -> dict:
    """Return a sample XJob as a raw dictionary (for deserialization tests)."""
    return {
        "name": "dict-test-job",
        "description": "Job constructed from a dict",
        "tags": ["test"],
        "labels": {"team": "qa"},
        "workflow": {
            "repo_name_or_path": "ix-hub/swe-rollout-verify",
            "params": {
                "scaffold": {
                    "repo_name_or_path": "ix-hub/swe-agent",
                    "id": "dummy",
                    "params": {},
                },
                "environment": {
                    "repo_name_or_path": "ix-hub/swe-bench",
                    "id": "django__django-12345",
                    "params": {},
                },
                "model": {
                    "type": "litellm",
                    "provider": "openai",
                    "model": "gpt-4o",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "sk-test-key",
                },
            },
        },
        "runtime": {
            "namespace": "default",
        },
    }
