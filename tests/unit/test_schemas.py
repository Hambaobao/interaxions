"""
Unit tests for schema models.

Covers: ScaffoldConfig, EnvironmentConfig, WorkflowConfig, RuntimeConfig,
        Environment (task data carrier), and XJob.
"""

import pytest
from pydantic import ValidationError

from interaxions.schemas import (
    EnvironmentConfig,
    Environment,
    RuntimeConfig,
    ScaffoldConfig,
    WorkflowConfig,
    XJob,
)


# ============================================================================
# ScaffoldConfig
# ============================================================================


@pytest.mark.unit
class TestScaffoldConfig:
    """Tests for ScaffoldConfig schema."""

    def test_minimal_creation(self):
        cfg = ScaffoldConfig(repo_name_or_path="ix-hub/swe-agent")
        assert cfg.repo_name_or_path == "ix-hub/swe-agent"
        assert cfg.revision is None
        assert cfg.username is None
        assert cfg.token is None
        assert cfg.params == {}

    def test_full_creation(self):
        cfg = ScaffoldConfig(
            repo_name_or_path="ix-hub/swe-agent",
            revision="v1.0.0",
            username="user",
            token="tok",
            params={"max_iterations": 50, "config": "default.yaml"},
        )
        assert cfg.revision == "v1.0.0"
        assert cfg.username == "user"
        assert cfg.token == "tok"
        assert cfg.params["max_iterations"] == 50
        assert cfg.params["config"] == "default.yaml"

    def test_params_default_empty_dict(self):
        cfg = ScaffoldConfig(repo_name_or_path="ix-hub/swe-agent")
        assert isinstance(cfg.params, dict)
        assert len(cfg.params) == 0

    def test_params_accepts_arbitrary_values(self):
        cfg = ScaffoldConfig(
            repo_name_or_path="test",
            params={"nested": {"key": "val"}, "list": [1, 2, 3], "flag": True},
        )
        assert cfg.params["nested"]["key"] == "val"
        assert cfg.params["list"] == [1, 2, 3]
        assert cfg.params["flag"] is True

    def test_missing_required_field(self):
        with pytest.raises(ValidationError) as exc_info:
            ScaffoldConfig()
        assert "repo_name_or_path" in str(exc_info.value)

    def test_serialization_roundtrip(self):
        original = ScaffoldConfig(
            repo_name_or_path="ix-hub/swe-agent",
            revision="v1.0.0",
            params={"key": "value"},
        )
        restored = ScaffoldConfig.model_validate(original.model_dump())
        assert restored.repo_name_or_path == original.repo_name_or_path
        assert restored.revision == original.revision
        assert restored.params == original.params

    def test_json_serialization_roundtrip(self):
        cfg = ScaffoldConfig(repo_name_or_path="ix-hub/agent", params={"a": 1})
        restored = ScaffoldConfig.model_validate_json(cfg.model_dump_json())
        assert restored.repo_name_or_path == cfg.repo_name_or_path
        assert restored.params == cfg.params


# ============================================================================
# EnvironmentConfig
# ============================================================================


@pytest.mark.unit
class TestEnvironmentConfig:
    """Tests for EnvironmentConfig schema."""

    def test_minimal_creation(self):
        cfg = EnvironmentConfig(
            repo_name_or_path="ix-hub/swe-bench",
            id="django__django-12345",
        )
        assert cfg.repo_name_or_path == "ix-hub/swe-bench"
        assert cfg.id == "django__django-12345"
        assert cfg.revision is None
        assert cfg.params == {}

    def test_full_creation(self):
        cfg = EnvironmentConfig(
            repo_name_or_path="ix-hub/swe-bench",
            revision="v2.0.0",
            username="u",
            token="t",
            id="astropy__astropy-12907",
            params={"predictions_path": "/tmp/out.jsonl", "fix_hack": True},
        )
        assert cfg.revision == "v2.0.0"
        assert cfg.id == "astropy__astropy-12907"
        assert cfg.params["predictions_path"] == "/tmp/out.jsonl"
        assert cfg.params["fix_hack"] is True

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentConfig(repo_name_or_path="ix-hub/swe-bench")
        assert "id" in str(exc_info.value)

    def test_missing_repo_name(self):
        with pytest.raises(ValidationError):
            EnvironmentConfig(id="some-id")

    def test_serialization_roundtrip(self):
        original = EnvironmentConfig(
            repo_name_or_path="ix-hub/swe-bench",
            id="django__django-12345",
            params={"split": "test"},
        )
        restored = EnvironmentConfig.model_validate(original.model_dump())
        assert restored.repo_name_or_path == original.repo_name_or_path
        assert restored.id == original.id
        assert restored.params == original.params

    def test_json_serialization_roundtrip(self):
        cfg = EnvironmentConfig(repo_name_or_path="ix-hub/bench", id="inst-1")
        restored = EnvironmentConfig.model_validate_json(cfg.model_dump_json())
        assert restored.id == cfg.id


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
                "scaffold": {"repo_name_or_path": "ix-hub/swe-agent", "id": "dummy", "params": {}},
                "environment": {"repo_name_or_path": "ix-hub/swe-bench", "id": "inst-1", "params": {}},
                "model": {"type": "litellm", "provider": "openai"},
            },
        )
        assert cfg.revision == "v3.0.0"
        assert cfg.params["scaffold"]["repo_name_or_path"] == "ix-hub/swe-agent"
        assert cfg.params["environment"]["id"] == "inst-1"

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
        assert rt.image_pull_policy == "IfNotPresent"
        assert rt.active_deadline_seconds is None
        assert rt.ttl_seconds_after_finished is None
        assert rt.extra_params == {}

    def test_full_creation(self):
        rt = RuntimeConfig(
            namespace="experiments",
            service_account="argo-workflow",
            image_pull_policy="Always",
            active_deadline_seconds=7200,
            ttl_seconds_after_finished=3600,
            extra_params={
                "labels": {"env": "prod", "team": "research"},
                "annotations": {"owner": "test@example.com"},
                "node_selector": {"gpu": "true"},
                "tolerations": [{"key": "dedicated", "value": "gpu"}],
            },
        )
        assert rt.namespace == "experiments"
        assert rt.service_account == "argo-workflow"
        assert rt.image_pull_policy == "Always"
        assert rt.active_deadline_seconds == 7200
        assert rt.ttl_seconds_after_finished == 3600
        assert rt.extra_params["labels"]["env"] == "prod"
        assert rt.extra_params["tolerations"][0]["key"] == "dedicated"

    def test_image_pull_policy_validation(self):
        """image_pull_policy must be 'Always' or 'IfNotPresent'."""
        with pytest.raises(ValidationError):
            RuntimeConfig(namespace="test", image_pull_policy="Never")

    def test_missing_required_namespace(self):
        with pytest.raises(ValidationError) as exc_info:
            RuntimeConfig()
        assert "namespace" in str(exc_info.value)

    def test_extra_params_flexible(self):
        rt = RuntimeConfig(
            namespace="test",
            extra_params={"priority_class_name": "high-priority", "custom": [1, 2]},
        )
        assert rt.extra_params["priority_class_name"] == "high-priority"
        assert rt.extra_params["custom"] == [1, 2]

    def test_serialization_roundtrip(self):
        original = RuntimeConfig(
            namespace="experiments",
            ttl_seconds_after_finished=1800,
            extra_params={"labels": {"k": "v"}},
        )
        restored = RuntimeConfig.model_validate(original.model_dump())
        assert restored.namespace == original.namespace
        assert restored.ttl_seconds_after_finished == original.ttl_seconds_after_finished
        assert restored.extra_params == original.extra_params

    def test_json_serialization_roundtrip(self):
        rt = RuntimeConfig(namespace="ns", service_account="sa")
        restored = RuntimeConfig.model_validate_json(rt.model_dump_json())
        assert restored.namespace == rt.namespace
        assert restored.service_account == rt.service_account


# ============================================================================
# Environment (data carrier from schemas.task)
# ============================================================================


@pytest.mark.unit
class TestEnvironment:
    """Tests for the Environment data carrier schema (interaxions.schemas.task)."""

    def test_minimal_creation(self):
        env = Environment(id="django__django-12345", type="swe-bench")
        assert env.id == "django__django-12345"
        assert env.type == "swe-bench"
        assert env.data == {}

    def test_full_creation(self):
        env = Environment(
            id="astropy__astropy-12907",
            type="swe-bench",
            data={
                "problem_statement": "Fix the bug in ...",
                "repo": "astropy/astropy",
                "base_commit": "abc123",
                "docker_image": "swe-bench:astropy",
            },
        )
        assert env.id == "astropy__astropy-12907"
        assert env.type == "swe-bench"
        assert env.data["problem_statement"] == "Fix the bug in ..."
        assert env.data["repo"] == "astropy/astropy"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            Environment()

    def test_missing_type(self):
        with pytest.raises(ValidationError):
            Environment(id="inst-1")

    def test_data_accepts_arbitrary_structure(self):
        env = Environment(
            id="test",
            type="custom",
            data={"nested": {"key": "val"}, "list": [1, 2, 3], "flag": True},
        )
        assert env.data["nested"]["key"] == "val"
        assert env.data["list"] == [1, 2, 3]

    def test_serialization_roundtrip(self):
        original = Environment(
            id="django__django-12345",
            type="swe-bench",
            data={"problem": "bug fix", "commit": "abc"},
        )
        restored = Environment.model_validate(original.model_dump())
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.data == original.data

    def test_json_serialization_roundtrip(self):
        env = Environment(id="inst-1", type="my-env", data={"k": "v"})
        restored = Environment.model_validate_json(env.model_dump_json())
        assert restored.id == env.id
        assert restored.data == env.data

    def test_subclass_can_extend(self):
        """Workflow-specific environment models can inherit Environment and add fields."""
        from pydantic import BaseModel

        class SWEEnvironment(Environment):
            fix_hack: bool = False

        swe_env = SWEEnvironment(
            id="django__django-12345",
            type="swe-bench",
            data={"problem": "bug"},
            fix_hack=True,
        )
        assert swe_env.fix_hack is True
        assert swe_env.id == "django__django-12345"
        assert swe_env.data["problem"] == "bug"

        # Still an Environment instance
        assert isinstance(swe_env, Environment)


# ============================================================================
# XJob
# ============================================================================


@pytest.mark.unit
class TestXJob:
    """Tests for XJob schema."""

    def test_minimal_creation(self, sample_workflow_config, sample_runtime_config):
        job = XJob(workflow=sample_workflow_config, runtime=sample_runtime_config)
        assert job.workflow == sample_workflow_config
        assert job.runtime == sample_runtime_config
        assert job.job_id is not None
        assert job.name is None
        assert job.description is None
        assert job.tags is None
        assert job.labels is None
        assert job.extra_params is None

    def test_job_id_auto_generated(self, sample_workflow_config, sample_runtime_config):
        job = XJob(workflow=sample_workflow_config, runtime=sample_runtime_config)
        assert job.job_id is not None
        assert job.job_id.startswith("job-")
        assert len(job.job_id) > 10

    def test_job_id_unique_each_time(self, sample_workflow_config, sample_runtime_config):
        job1 = XJob(workflow=sample_workflow_config, runtime=sample_runtime_config)
        job2 = XJob(workflow=sample_workflow_config, runtime=sample_runtime_config)
        assert job1.job_id != job2.job_id

    def test_custom_job_id(self, sample_workflow_config, sample_runtime_config):
        job = XJob(
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
            XJob(runtime=sample_runtime_config)
        assert "workflow" in str(exc_info.value)

    def test_missing_required_runtime(self, sample_workflow_config):
        with pytest.raises(ValidationError) as exc_info:
            XJob(workflow=sample_workflow_config)
        assert "runtime" in str(exc_info.value)

    def test_workflow_params_contains_components(self, sample_job):
        """All component configs (scaffold, env, model) live in workflow.params."""
        params = sample_job.workflow.params
        assert "scaffold" in params
        assert "environment" in params
        assert "model" in params
        assert params["scaffold"]["repo_name_or_path"] == "ix-hub/swe-agent"
        assert params["environment"]["id"] == "astropy__astropy-12907"
        assert params["model"]["type"] == "litellm"

    def test_json_serialization_roundtrip(self, sample_job):
        json_str = sample_job.model_dump_json()
        restored = XJob.model_validate_json(json_str)
        assert restored.name == sample_job.name
        assert restored.workflow.repo_name_or_path == sample_job.workflow.repo_name_or_path
        assert restored.runtime.namespace == sample_job.runtime.namespace
        assert restored.workflow.params == sample_job.workflow.params

    def test_from_dict(self, sample_job_dict):
        job = XJob.model_validate(sample_job_dict)
        assert job.name == "dict-test-job"
        assert job.workflow.repo_name_or_path == "ix-hub/swe-rollout-verify"
        assert job.runtime.namespace == "default"
        assert job.workflow.params["environment"]["id"] == "django__django-12345"

    def test_tags_list(self, sample_workflow_config, sample_runtime_config):
        job = XJob(
            workflow=sample_workflow_config,
            runtime=sample_runtime_config,
            tags=["alpha", "beta", "gamma"],
        )
        assert len(job.tags) == 3
        assert "alpha" in job.tags

    def test_labels_dict(self, sample_workflow_config, sample_runtime_config):
        job = XJob(
            workflow=sample_workflow_config,
            runtime=sample_runtime_config,
            labels={"env": "staging", "version": "2"},
        )
        assert job.labels["env"] == "staging"
        assert job.labels["version"] == "2"

    def test_extra_params_optional(self, sample_workflow_config, sample_runtime_config):
        job = XJob(
            workflow=sample_workflow_config,
            runtime=sample_runtime_config,
            extra_params={"debug": True, "dry_run": False},
        )
        assert job.extra_params["debug"] is True

    def test_persistence_to_file(self, sample_job, tmp_path):
        """XJob can be saved as JSON and loaded back."""
        job_file = tmp_path / "job.json"
        job_file.write_text(sample_job.model_dump_json(indent=2))

        loaded = XJob.model_validate_json(job_file.read_text())
        assert loaded.name == sample_job.name
        assert loaded.workflow.params == sample_job.workflow.params
        assert loaded.runtime.namespace == sample_job.runtime.namespace
