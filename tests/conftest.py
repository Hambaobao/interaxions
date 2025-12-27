"""
Pytest configuration and shared fixtures for all tests.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest
from freezegun import freeze_time

from interaxions.schemas import (
    Environment,
    XJob,
    LiteLLMModel,
    Runtime,
    Scaffold,
    Workflow,
)

# ============================================================================
# Path Fixtures
# ============================================================================


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def tests_dir(project_root) -> Path:
    """Return the tests directory."""
    return project_root / "tests"


@pytest.fixture
def fixtures_dir(tests_dir) -> Path:
    """Return the fixtures directory."""
    return tests_dir / "fixtures"


@pytest.fixture
def mock_repos_dir(fixtures_dir) -> Path:
    """Return the mock repositories directory."""
    return fixtures_dir / "mock_repos"


# ============================================================================
# Schema Fixtures
# ============================================================================


@pytest.fixture
def sample_model() -> LiteLLMModel:
    """Return a sample LiteLLM model configuration."""
    return LiteLLMModel(
        type="litellm",
        provider="openai",
        model="gpt-4",
        base_url="https://api.openai.com/v1",
        api_key="sk-test-key",
        temperature=0.7,
    )


@pytest.fixture
def sample_scaffold() -> Scaffold:
    """Return a sample scaffold configuration."""
    return Scaffold(
        repo_name_or_path="swe-agent",
        revision=None,
        params={
            "sweagent_config": "default.yaml",
            "tools_parse_function": "python",
            "max_iterations": 10,
        },
    )


@pytest.fixture
def sample_environment() -> Environment:
    """Return a sample environment configuration (HF source)."""
    return Environment(
        repo_name_or_path="swe-bench",
        revision=None,
        environment_id="astropy__astropy-12907",
        source="hf",
        params={
            "dataset": "princeton-nlp/SWE-bench",
            "split": "test",
            "predictions_path": "gold",
        },
    )


@pytest.fixture
def sample_environment_oss() -> Environment:
    """Return a sample environment configuration (OSS source)."""
    return Environment(
        repo_name_or_path="swe-bench",
        revision=None,
        environment_id="astropy__astropy-12907",
        source="oss",
        params={
            "dataset": "swe-bench",
            "split": "test",
            "oss_region": "cn-hangzhou",
            "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
            "oss_access_key_id": "test-key-id",
            "oss_access_key_secret": "test-secret",
            "predictions_path": "gold",
        },
    )


@pytest.fixture
def sample_workflow() -> Workflow:
    """Return a sample workflow configuration."""
    return Workflow(
        repo_name_or_path="rollout-and-verify",
        revision=None,
        params={},
    )


@pytest.fixture
def sample_runtime() -> Runtime:
    """Return a sample runtime configuration."""
    return Runtime(
        namespace="experiments",
        service_account="argo-workflow",
        image_pull_policy="IfNotPresent",
        ttl_seconds_after_finished=3600,
        extra_params={
            "labels": {
                "project": "interaxions"
            },
            "annotations": {
                "description": "Test workflow"
            },
        },
    )


@pytest.fixture
@freeze_time("2025-01-01 12:00:00")
def sample_job(
    sample_model: LiteLLMModel,
    sample_scaffold: Scaffold,
    sample_environment: Environment,
    sample_workflow: Workflow,
    sample_runtime: Runtime,
) -> XJob:
    """Return a complete sample XJob with all components."""
    return XJob(
        job_id=None,  # Will be auto-generated
        name="test-job",
        description="A test job for unit testing",
        tags=["test", "unit"],
        labels={
            "team": "qa",
            "priority": "high"
        },
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        finished_at=None,
        model=sample_model,
        scaffold=sample_scaffold,
        environment=sample_environment,
        workflow=sample_workflow,
        runtime=sample_runtime,
    )


@pytest.fixture
def sample_job_dict() -> Dict[str, Any]:
    """Return a sample XJob as a dictionary."""
    return {
        "name": "test-job",
        "description": "A test job",
        "tags": ["test"],
        "labels": {
            "team": "qa"
        },
        "model": {
            "type": "litellm",
            "provider": "openai",
            "model": "gpt-4",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
        },
        "scaffold": {
            "repo_name_or_path": "swe-agent",
            "params": {},
        },
        "environment": {
            "repo_name_or_path": "swe-bench",
            "environment_id": "test-123",
            "source": "hf",
            "params": {
                "dataset": "test-dataset",
                "split": "test",
            },
        },
        "workflow": {
            "repo_name_or_path": "rollout-and-verify",
            "params": {},
        },
        "runtime": {
            "namespace": "default",
        },
    }


# ============================================================================
# Mock Data Fixtures
# ============================================================================


@pytest.fixture
def mock_config_yaml(tmp_path: Path) -> Path:
    """Create a temporary config.yaml file."""
    config_path = tmp_path / "config.yaml"
    config_content = """
type: test-type
test_param: test_value
nested:
  key: value
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def mock_template_file(tmp_path: Path) -> Path:
    """Create a temporary Jinja2 template file."""
    template_path = tmp_path / "template.j2"
    template_content = """
Hello {{ name }}!
Value: {{ value }}
"""
    template_path.write_text(template_content)
    return template_path


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def frozen_time():
    """Freeze time for deterministic timestamp testing."""
    with freeze_time("2025-01-01 12:00:00"):
        yield datetime(2025, 1, 1, 12, 0, 0)
