"""
Unit tests for schema models (XJob, Scaffold, Environment, Workflow, Runtime).
"""

from datetime import datetime
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from interaxions.schemas import Environment, XJob, Runtime, Scaffold, Workflow


@pytest.mark.unit
class TestScaffold:
    """Tests for Scaffold schema."""

    def test_scaffold_creation_minimal(self):
        """Test creating a scaffold with minimal required fields."""
        scaffold = Scaffold(repo_name_or_path="swe-agent",)
        assert scaffold.repo_name_or_path == "swe-agent"
        assert scaffold.revision is None
        assert scaffold.params == {}

    def test_scaffold_creation_full(self):
        """Test creating a scaffold with all fields."""
        scaffold = Scaffold(
            repo_name_or_path="swe-agent",
            revision="v1.0.0",
            params={
                "max_iterations": 10,
                "config": "default.yaml"
            },
        )
        assert scaffold.repo_name_or_path == "swe-agent"
        assert scaffold.revision == "v1.0.0"
        assert scaffold.params["max_iterations"] == 10
        assert scaffold.params["config"] == "default.yaml"

    def test_scaffold_serialization(self):
        """Test scaffold serialization and deserialization."""
        original = Scaffold(
            repo_name_or_path="swe-agent",
            revision="main",
            params={"test": "value"},
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["repo_name_or_path"] == "swe-agent"

        # Deserialize from dict
        restored = Scaffold.model_validate(data)
        assert restored.repo_name_or_path == original.repo_name_or_path
        assert restored.revision == original.revision
        assert restored.params == original.params

    def test_scaffold_json_serialization(self):
        """Test scaffold JSON serialization."""
        scaffold = Scaffold(
            repo_name_or_path="test-scaffold",
            params={"key": "value"},
        )

        # To JSON
        json_str = scaffold.model_dump_json()
        assert "test-scaffold" in json_str

        # From JSON
        restored = Scaffold.model_validate_json(json_str)
        assert restored.repo_name_or_path == scaffold.repo_name_or_path


@pytest.mark.unit
class TestEnvironment:
    """Tests for Environment schema."""

    def test_environment_creation_hf(self):
        """Test creating an environment with HF source."""
        env = Environment(
            repo_name_or_path="swe-bench",
            environment_id="astropy__astropy-12907",
            source="hf",
            params={
                "dataset": "princeton-nlp/SWE-bench",
                "split": "test",
            },
        )
        assert env.repo_name_or_path == "swe-bench"
        assert env.environment_id == "astropy__astropy-12907"
        assert env.source == "hf"
        assert env.params["dataset"] == "princeton-nlp/SWE-bench"

    def test_environment_creation_oss(self):
        """Test creating an environment with OSS source."""
        env = Environment(
            repo_name_or_path="swe-bench",
            environment_id="test-123",
            source="oss",
            params={
                "dataset": "test-dataset",
                "split": "test",
                "oss_region": "cn-hangzhou",
            },
        )
        assert env.source == "oss"
        assert env.params["oss_region"] == "cn-hangzhou"

    def test_environment_custom_source(self):
        """Test creating an environment with custom source."""
        env = Environment(
            repo_name_or_path="custom-env",
            environment_id="custom-123",
            source="s3",
            params={"bucket": "my-bucket"},
        )
        assert env.source == "s3"
        assert env.params["bucket"] == "my-bucket"

    def test_environment_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Environment(repo_name_or_path="test",
                        # Missing environment_id and source
                       )
        assert "environment_id" in str(exc_info.value)
        assert "source" in str(exc_info.value)


@pytest.mark.unit
class TestWorkflow:
    """Tests for Workflow schema."""

    def test_workflow_creation_minimal(self):
        """Test creating a workflow with minimal fields."""
        workflow = Workflow(repo_name_or_path="rollout-and-verify")
        assert workflow.repo_name_or_path == "rollout-and-verify"
        assert workflow.revision is None
        assert workflow.params == {}

    def test_workflow_creation_with_params(self):
        """Test creating a workflow with parameters."""
        workflow = Workflow(
            repo_name_or_path="custom-workflow",
            revision="v2.0",
            params={
                "timeout": 3600,
                "retries": 3
            },
        )
        assert workflow.params["timeout"] == 3600
        assert workflow.params["retries"] == 3


@pytest.mark.unit
class TestRuntime:
    """Tests for Runtime schema."""

    def test_runtime_creation_minimal(self):
        """Test creating runtime with required namespace."""
        runtime = Runtime(namespace="default")
        assert runtime.namespace == "default"
        assert runtime.service_account is None
        assert runtime.image_pull_policy == "IfNotPresent"
        assert runtime.ttl_seconds_after_finished is None
        assert runtime.extra_params == {}

    def test_runtime_creation_full(self):
        """Test creating runtime with all fields."""
        runtime = Runtime(
            namespace="experiments",
            service_account="argo-workflow",
            image_pull_policy="Always",
            ttl_seconds_after_finished=3600,
            extra_params={
                "labels": {
                    "project": "test"
                },
                "annotations": {
                    "description": "test run"
                },
            },
        )
        assert runtime.namespace == "experiments"
        assert runtime.service_account == "argo-workflow"
        assert runtime.image_pull_policy == "Always"
        assert runtime.ttl_seconds_after_finished == 3600
        assert runtime.extra_params["labels"]["project"] == "test"

    def test_runtime_extra_params_flexible(self):
        """Test that extra_params accepts arbitrary data."""
        runtime = Runtime(
            namespace="test",
            extra_params={
                "custom_field": "value",
                "nested": {
                    "key": "value"
                },
                "list_data": [1, 2, 3],
            }
        )
        assert runtime.extra_params["custom_field"] == "value"
        assert runtime.extra_params["nested"]["key"] == "value"
        assert runtime.extra_params["list_data"] == [1, 2, 3]


@pytest.mark.unit
class TestXJob:
    """Tests for XJob schema."""

    def test_job_creation_minimal(self, sample_model, sample_scaffold, sample_environment, sample_workflow, sample_runtime):
        """Test creating a job with minimal required fields."""
        job = XJob(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            runtime=sample_runtime,
        )
        assert job.model == sample_model
        assert job.scaffold == sample_scaffold
        assert job.environment == sample_environment
        assert job.workflow == sample_workflow
        assert job.runtime == sample_runtime

    def test_job_id_auto_generation(self, sample_model, sample_scaffold, sample_environment, sample_workflow, sample_runtime):
        """Test that job_id is auto-generated if not provided."""
        job = XJob(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            runtime=sample_runtime,
        )
        assert job.job_id is not None
        assert job.job_id.startswith("job-")
        assert len(job.job_id) > 10  # UUID format

    def test_job_id_custom(self, sample_model, sample_scaffold, sample_environment, sample_workflow, sample_runtime):
        """Test providing a custom job_id."""
        custom_id = "custom-job-12345"
        job = XJob(
            job_id=custom_id,
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            runtime=sample_runtime,
        )
        assert job.job_id == custom_id

    def test_job_with_metadata(self, sample_job):
        """Test job with full metadata."""
        assert sample_job.name == "test-job"
        assert sample_job.description == "A test job for unit testing"
        assert "test" in sample_job.tags
        assert "unit" in sample_job.tags
        assert sample_job.labels["team"] == "qa"
        assert sample_job.labels["priority"] == "high"

    def test_job_timestamps(self, sample_job):
        """Test job timestamp fields."""
        assert sample_job.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert sample_job.finished_at is None

    def test_job_serialization_json(self, sample_job):
        """Test job serialization to JSON."""
        json_str = sample_job.model_dump_json()
        assert "test-job" in json_str
        assert "swe-agent" in json_str
        assert "astropy__astropy-12907" in json_str

        # Deserialize
        restored = XJob.model_validate_json(json_str)
        assert restored.name == sample_job.name
        assert restored.scaffold.repo_name_or_path == sample_job.scaffold.repo_name_or_path
        assert restored.environment.environment_id == sample_job.environment.environment_id

    def test_job_from_dict(self, sample_job_dict):
        """Test creating job from dictionary."""
        job = XJob.model_validate(sample_job_dict)
        assert job.name == "test-job"
        assert job.model.provider == "openai"
        assert job.scaffold.repo_name_or_path == "swe-agent"
        assert job.environment.source == "hf"

    def test_job_flexible_composition(self, sample_workflow, sample_runtime):
        """Test that XJob allows flexible composition of components."""
        # XJob with only workflow and runtime (minimum required)
        job_minimal = XJob(workflow=sample_workflow, runtime=sample_runtime)
        assert job_minimal.job_id is not None  # Auto-generated
        assert job_minimal.model is None
        assert job_minimal.scaffold is None
        assert job_minimal.environment is None
        assert job_minimal.workflow is not None  # Required
        assert job_minimal.runtime is not None  # Required

        # XJob with workflow, runtime and name
        job_named = XJob(name="test-job", workflow=sample_workflow, runtime=sample_runtime)
        assert job_named.name == "test-job"
        assert job_named.model is None
        assert job_named.workflow is not None
        assert job_named.runtime is not None

    def test_job_tags_optional(self, sample_model, sample_scaffold, sample_environment, sample_workflow, sample_runtime):
        """Test that tags are optional."""
        job = XJob(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            runtime=sample_runtime,
            tags=None,
        )
        assert job.tags is None

    def test_job_tags_as_list(self, sample_model, sample_scaffold, sample_environment, sample_workflow, sample_runtime):
        """Test that tags accept list of strings."""
        job = XJob(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            runtime=sample_runtime,
            tags=["tag1", "tag2", "tag3"],
        )
        assert len(job.tags) == 3
        assert "tag1" in job.tags

    def test_job_labels_optional(self, sample_model, sample_scaffold, sample_environment, sample_workflow, sample_runtime):
        """Test that labels are optional."""
        job = XJob(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            runtime=sample_runtime,
            labels=None,
        )
        assert job.labels is None

    def test_job_finished_at_optional(self, sample_job):
        """Test that finished_at can be set."""
        assert sample_job.finished_at is None

        # Update finished_at
        finish_time = datetime(2025, 1, 1, 13, 0, 0)
        sample_job.finished_at = finish_time
        assert sample_job.finished_at == finish_time

    def test_job_complete_workflow(self, sample_job):
        """Test that a complete job has all components."""
        # Verify all components are present
        assert sample_job.model is not None
        assert sample_job.scaffold is not None
        assert sample_job.environment is not None
        assert sample_job.workflow is not None
        assert sample_job.runtime is not None

        # Verify component types
        assert sample_job.model.type == "litellm"
        assert sample_job.scaffold.repo_name_or_path == "swe-agent"
        assert sample_job.environment.source == "hf"
        assert sample_job.workflow.repo_name_or_path == "rollout-and-verify"
        assert sample_job.runtime.namespace == "experiments"
