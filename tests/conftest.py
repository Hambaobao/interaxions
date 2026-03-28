"""
Pytest configuration and shared fixtures for all tests.
"""

from pathlib import Path

import pytest

from interaxions.schemas import (
    Job,
    RuntimeConfig,
    WorkflowConfig,
)
from interaxions.schemas.runtime import TTLConfig, RetryConfig, BackoffConfig


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
def mock_workflow_repo(mock_repos_dir: Path) -> Path:
    """Return the test-workflow mock repo path."""
    return mock_repos_dir / "test-workflow"


@pytest.fixture
def mock_task_repo(mock_repos_dir: Path) -> Path:
    """Return the test-task mock repo path."""
    return mock_repos_dir / "test-task"


@pytest.fixture
def mock_declarative_workflow_repo(mock_repos_dir: Path) -> Path:
    """Return the test-declarative-workflow mock repo path."""
    return mock_repos_dir / "test-declarative-workflow"


# ============================================================================
# Schema Fixtures
# ============================================================================


@pytest.fixture
def sample_workflow_config() -> WorkflowConfig:
    """Return a sample WorkflowConfig."""
    return WorkflowConfig(
        repo_name_or_path="ix-hub/swe-rollout-verify",
        revision="v1.0.0",
        params={
            "instance_id": "astropy__astropy-12907",
            "agent": {
                "repo_name_or_path": "ix-hub/swe-agent",
                "max_iterations": 50,
            },
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
        ttl=TTLConfig(seconds_after_success=60, seconds_after_failure=3600),
        labels={"project": "interaxions", "team": "research"},
        annotations={"description": "Test workflow"},
        node_selector={"gpu": "true"},
    )


@pytest.fixture
def sample_job(
    sample_workflow_config: WorkflowConfig,
    sample_runtime_config: RuntimeConfig,
) -> Job:
    """Return a complete sample Job."""
    return Job(
        name="test-swe-bench-job",
        description="A test SWE-bench job for unit testing",
        tags=["test", "swe-bench", "unit"],
        labels={"team": "research", "priority": "high"},
        workflow=sample_workflow_config,
        runtime=sample_runtime_config,
    )


@pytest.fixture
def sample_job_dict() -> dict:
    """Return a sample Job as a raw dictionary (for deserialization tests)."""
    return {
        "name": "dict-test-job",
        "description": "Job constructed from a dict",
        "tags": ["test"],
        "labels": {"team": "qa"},
        "workflow": {
            "repo_name_or_path": "ix-hub/swe-rollout-verify",
            "params": {
                "instance_id": "django__django-12345",
                "agent": {
                    "repo_name_or_path": "ix-hub/swe-agent",
                    "max_iterations": 50,
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
