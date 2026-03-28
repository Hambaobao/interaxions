"""
Unit tests for schema models.

Covers: WorkflowConfig, RuntimeConfig, and Job.
"""

import pytest
from pydantic import ValidationError

from interaxions.schemas import (
    Job,
    RuntimeConfig,
    WorkflowConfig,
)
from interaxions.schemas.runtime import TTLConfig, BackoffConfig, RetryConfig


# ============================================================================
# WorkflowConfig
# ============================================================================


@pytest.mark.unit
class TestWorkflowConfig:
    """Tests for WorkflowConfig schema."""

    def test_minimal_creation(self):
        cfg = WorkflowConfig(repo_name_or_path="ix-hub/swe-rollout-verify")
        assert cfg.repo_name_or_path == "ix-hub/swe-rollout-verify"
        assert cfg.revision is None
        assert cfg.params == {}

    def test_full_creation(self):
        cfg = WorkflowConfig(
            repo_name_or_path="ix-hub/swe-rollout-verify",
            revision="v3.0.0",
            username="u",
            token="tok",
            params={
                "instance_id": "django__django-12345",
                "agent": {"repo_name_or_path": "ix-hub/swe-agent", "max_iterations": 50},
                "model": {"type": "litellm", "provider": "openai"},
            },
        )
        assert cfg.revision == "v3.0.0"
        assert cfg.params["instance_id"] == "django__django-12345"
        assert cfg.params["agent"]["repo_name_or_path"] == "ix-hub/swe-agent"

    def test_params_holds_arbitrary_workflow_config(self):
        """Workflow params are fully open — any shape is valid."""
        cfg = WorkflowConfig(
            repo_name_or_path="ix-hub/custom-workflow",
            params={"custom_key": "custom_value", "threshold": 0.9, "steps": [1, 2, 3]},
        )
        assert cfg.params["custom_key"] == "custom_value"
        assert cfg.params["threshold"] == 0.9

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            WorkflowConfig()

    def test_serialization_roundtrip(self):
        original = WorkflowConfig(
            repo_name_or_path="ix-hub/wf",
            revision="v1",
            params={"a": {"b": "c"}},
        )
        restored = WorkflowConfig.model_validate(original.model_dump())
        assert restored.repo_name_or_path == original.repo_name_or_path
        assert restored.params == original.params


# ============================================================================
# RuntimeConfig
# ============================================================================


@pytest.mark.unit
class TestRuntimeConfig:
    """Tests for RuntimeConfig schema."""

    def test_minimal_creation(self):
        rt = RuntimeConfig(namespace="default")
        assert rt.namespace == "default"
        assert rt.service_account is None
        assert rt.active_deadline_seconds is None
        assert rt.ttl is None
        assert rt.retry is None

    def test_missing_required_namespace(self):
        with pytest.raises(ValidationError) as exc_info:
            RuntimeConfig()
        assert "namespace" in str(exc_info.value)

    def test_full_creation(self):
        rt = RuntimeConfig(
            namespace="experiments",
            service_account="argo-workflow",
            active_deadline_seconds=7200,
            ttl=TTLConfig(seconds_after_success=60, seconds_after_failure=1800),
            retry=RetryConfig(limit=3, backoff=BackoffConfig(duration="1m", factor=2)),
            dns_policy="ClusterFirst",
            pod_gc_strategy="OnWorkflowSuccess",
            pod_priority_class_name="high-priority",
            node_selector={"gpu": "true"},
            tolerations=[{"key": "dedicated", "value": "gpu"}],
            labels={"env": "prod", "team": "research"},
            annotations={"owner": "test@example.com"},
        )
        assert rt.namespace == "experiments"
        assert rt.service_account == "argo-workflow"
        assert rt.active_deadline_seconds == 7200
        assert rt.ttl.seconds_after_success == 60
        assert rt.ttl.seconds_after_failure == 1800
        assert rt.retry.limit == 3
        assert rt.retry.backoff.duration == "1m"
        assert rt.dns_policy == "ClusterFirst"
        assert rt.pod_gc_strategy == "OnWorkflowSuccess"
        assert rt.node_selector["gpu"] == "true"
        assert rt.labels["env"] == "prod"

    def test_ttl_config(self):
        ttl = TTLConfig(seconds_after_finished=3600)
        assert ttl.seconds_after_finished == 3600
        assert ttl.seconds_after_success is None
        assert ttl.seconds_after_failure is None

    def test_ttl_success_failure_split(self):
        ttl = TTLConfig(seconds_after_success=60, seconds_after_failure=1800)
        assert ttl.seconds_after_success == 60
        assert ttl.seconds_after_failure == 1800
        assert ttl.seconds_after_finished is None

    def test_retry_config_defaults(self):
        retry = RetryConfig()
        assert retry.limit == 3
        assert retry.policy == "Always"
        assert retry.backoff is None

    def test_retry_config_with_backoff(self):
        retry = RetryConfig(limit=5, policy="OnFailure", backoff=BackoffConfig(duration="30s", factor=3))
        assert retry.limit == 5
        assert retry.policy == "OnFailure"
        assert retry.backoff.duration == "30s"
        assert retry.backoff.factor == 3

    def test_serialization_roundtrip(self):
        original = RuntimeConfig(
            namespace="experiments",
            ttl=TTLConfig(seconds_after_success=60, seconds_after_failure=1800),
            retry=RetryConfig(limit=3, backoff=BackoffConfig(duration="1m")),
            labels={"k": "v"},
        )
        restored = RuntimeConfig.model_validate(original.model_dump())
        assert restored.namespace == original.namespace
        assert restored.ttl.seconds_after_success == original.ttl.seconds_after_success
        assert restored.retry.limit == original.retry.limit
        assert restored.labels == original.labels

    def test_json_serialization_roundtrip(self):
        rt = RuntimeConfig(
            namespace="ns",
            service_account="sa",
            ttl=TTLConfig(seconds_after_finished=3600),
        )
        restored = RuntimeConfig.model_validate_json(rt.model_dump_json())
        assert restored.namespace == rt.namespace
        assert restored.service_account == rt.service_account
        assert restored.ttl.seconds_after_finished == rt.ttl.seconds_after_finished


# ============================================================================
# Job
# ============================================================================


@pytest.mark.unit
class TestJob:
    """Tests for Job schema."""

    def test_minimal_creation(self, sample_workflow_config, sample_runtime_config):
        job = Job(workflow=sample_workflow_config, runtime=sample_runtime_config)
        assert job.workflow == sample_workflow_config
        assert job.runtime == sample_runtime_config
        assert job.job_id is not None
        assert job.name is None
        assert job.description is None
        assert job.tags is None
        assert job.labels is None
        assert job.extra_params is None

    def test_job_id_auto_generated(self, sample_workflow_config, sample_runtime_config):
        job = Job(workflow=sample_workflow_config, runtime=sample_runtime_config)
        assert job.job_id is not None
        assert job.job_id.startswith("job-")
        assert len(job.job_id) > 10

    def test_job_id_unique_each_time(self, sample_workflow_config, sample_runtime_config):
        job1 = Job(workflow=sample_workflow_config, runtime=sample_runtime_config)
        job2 = Job(workflow=sample_workflow_config, runtime=sample_runtime_config)
        assert job1.job_id != job2.job_id

    def test_custom_job_id(self, sample_workflow_config, sample_runtime_config):
        job = Job(
            job_id="custom-job-abc123",
            workflow=sample_workflow_config,
            runtime=sample_runtime_config,
        )
        assert job.job_id == "custom-job-abc123"

    def test_full_metadata(self, sample_job):
        assert sample_job.name == "test-swe-bench-job"
        assert sample_job.description == "A test SWE-bench job for unit testing"
        assert "test" in sample_job.tags
        assert "swe-bench" in sample_job.tags
        assert sample_job.labels["team"] == "research"
        assert sample_job.labels["priority"] == "high"

    def test_missing_required_workflow(self, sample_runtime_config):
        with pytest.raises(ValidationError) as exc_info:
            Job(runtime=sample_runtime_config)
        assert "workflow" in str(exc_info.value)

    def test_missing_required_runtime(self, sample_workflow_config):
        with pytest.raises(ValidationError) as exc_info:
            Job(workflow=sample_workflow_config)
        assert "runtime" in str(exc_info.value)

    def test_workflow_params_shape(self, sample_job):
        """All task configs live in workflow.params — no fixed schema."""
        params = sample_job.workflow.params
        assert "instance_id" in params
        assert "agent" in params
        assert "model" in params
        assert params["agent"]["repo_name_or_path"] == "ix-hub/swe-agent"
        assert params["instance_id"] == "astropy__astropy-12907"
        assert params["model"]["type"] == "litellm"

    def test_json_serialization_roundtrip(self, sample_job):
        json_str = sample_job.model_dump_json()
        restored = Job.model_validate_json(json_str)
        assert restored.name == sample_job.name
        assert restored.workflow.repo_name_or_path == sample_job.workflow.repo_name_or_path
        assert restored.runtime.namespace == sample_job.runtime.namespace
        assert restored.workflow.params == sample_job.workflow.params

    def test_from_dict(self, sample_job_dict):
        job = Job.model_validate(sample_job_dict)
        assert job.name == "dict-test-job"
        assert job.workflow.repo_name_or_path == "ix-hub/swe-rollout-verify"
        assert job.runtime.namespace == "default"
        assert job.workflow.params["instance_id"] == "django__django-12345"

    def test_tags_list(self, sample_workflow_config, sample_runtime_config):
        job = Job(
            workflow=sample_workflow_config,
            runtime=sample_runtime_config,
            tags=["alpha", "beta", "gamma"],
        )
        assert len(job.tags) == 3
        assert "alpha" in job.tags

    def test_labels_dict(self, sample_workflow_config, sample_runtime_config):
        job = Job(
            workflow=sample_workflow_config,
            runtime=sample_runtime_config,
            labels={"env": "staging", "version": "2"},
        )
        assert job.labels["env"] == "staging"
        assert job.labels["version"] == "2"

    def test_extra_params_optional(self, sample_workflow_config, sample_runtime_config):
        job = Job(
            workflow=sample_workflow_config,
            runtime=sample_runtime_config,
            extra_params={"debug": True, "dry_run": False},
        )
        assert job.extra_params["debug"] is True

    def test_persistence_to_file(self, sample_job, tmp_path):
        """Job can be saved as JSON and loaded back."""
        job_file = tmp_path / "job.json"
        job_file.write_text(sample_job.model_dump_json(indent=2))

        loaded = Job.model_validate_json(job_file.read_text())
        assert loaded.name == sample_job.name
        assert loaded.workflow.params == sample_job.workflow.params
        assert loaded.runtime.namespace == sample_job.runtime.namespace
