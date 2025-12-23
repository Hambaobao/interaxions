"""
Unit tests for schema models (Job, Scaffold, Environment, Workflow, Runtime).
"""

from datetime import datetime
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from interaxions.schemas import Environment, Job, Runtime, Scaffold, Workflow


@pytest.mark.unit
class TestScaffold:
    """Tests for Scaffold schema."""

    def test_scaffold_creation_minimal(self):
        """Test creating a scaffold with minimal required fields."""
        scaffold = Scaffold(
            repo_name_or_path="swe-agent",
        )
        assert scaffold.repo_name_or_path == "swe-agent"
        assert scaffold.revision is None
        assert scaffold.params == {}

    def test_scaffold_creation_full(self):
        """Test creating a scaffold with all fields."""
        scaffold = Scaffold(
            repo_name_or_path="swe-agent",
            revision="v1.0.0",
            params={"max_iterations": 10, "config": "default.yaml"},
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
            environment_id="django__django-12345",
            source="hf",
            params={
                "dataset": "princeton-nlp/SWE-bench",
                "split": "test",
            },
        )
        assert env.repo_name_or_path == "swe-bench"
        assert env.environment_id == "django__django-12345"
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
            Environment(
                repo_name_or_path="test",
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
            params={"timeout": 3600, "retries": 3},
        )
        assert workflow.params["timeout"] == 3600
        assert workflow.params["retries"] == 3


@pytest.mark.unit
class TestRuntime:
    """Tests for Runtime schema."""

    def test_runtime_creation_minimal(self):
        """Test creating runtime with default values."""
        runtime = Runtime()
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
                "labels": {"project": "test"},
                "annotations": {"description": "test run"},
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
            extra_params={
                "custom_field": "value",
                "nested": {"key": "value"},
                "list_data": [1, 2, 3],
            }
        )
        assert runtime.extra_params["custom_field"] == "value"
        assert runtime.extra_params["nested"]["key"] == "value"
        assert runtime.extra_params["list_data"] == [1, 2, 3]


@pytest.mark.unit
class TestJob:
    """Tests for Job schema."""

    def test_job_creation_minimal(self, sample_model, sample_scaffold, sample_environment, sample_workflow):
        """Test creating a job with minimal required fields."""
        job = Job(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
        )
        assert job.model == sample_model
        assert job.scaffold == sample_scaffold
        assert job.environment == sample_environment
        assert job.workflow == sample_workflow
        assert job.runtime.namespace == "default"  # Default runtime

    def test_job_id_auto_generation(self, sample_model, sample_scaffold, sample_environment, sample_workflow):
        """Test that job_id is auto-generated if not provided."""
        job = Job(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
        )
        assert job.job_id is not None
        assert job.job_id.startswith("job-")
        assert len(job.job_id) > 10  # UUID format

    def test_job_id_custom(self, sample_model, sample_scaffold, sample_environment, sample_workflow):
        """Test providing a custom job_id."""
        custom_id = "custom-job-12345"
        job = Job(
            job_id=custom_id,
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
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
        assert "django__django-12345" in json_str
        
        # Deserialize
        restored = Job.model_validate_json(json_str)
        assert restored.name == sample_job.name
        assert restored.scaffold.repo_name_or_path == sample_job.scaffold.repo_name_or_path
        assert restored.environment.environment_id == sample_job.environment.environment_id

    def test_job_from_dict(self, sample_job_dict):
        """Test creating job from dictionary."""
        job = Job.model_validate(sample_job_dict)
        assert job.name == "test-job"
        assert job.model.provider == "openai"
        assert job.scaffold.repo_name_or_path == "swe-agent"
        assert job.environment.source == "hf"

    def test_job_validation_missing_required(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Job(
                # Missing all required fields
            )
        assert "model" in str(exc_info.value).lower()
        assert "scaffold" in str(exc_info.value).lower()
        assert "environment" in str(exc_info.value).lower()
        assert "workflow" in str(exc_info.value).lower()

    def test_job_tags_optional(self, sample_model, sample_scaffold, sample_environment, sample_workflow):
        """Test that tags are optional."""
        job = Job(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            tags=None,
        )
        assert job.tags is None

    def test_job_tags_as_list(self, sample_model, sample_scaffold, sample_environment, sample_workflow):
        """Test that tags accept list of strings."""
        job = Job(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
            tags=["tag1", "tag2", "tag3"],
        )
        assert len(job.tags) == 3
        assert "tag1" in job.tags

    def test_job_labels_optional(self, sample_model, sample_scaffold, sample_environment, sample_workflow):
        """Test that labels are optional."""
        job = Job(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
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

