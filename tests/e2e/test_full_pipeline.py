"""
End-to-end tests for the complete XJob → component loading pipeline.

These tests exercise the full flow:
  XJob (schema) → AutoWorkflow/AutoScaffold/AutoEnvironment (loading)
  → BaseEnvironment.get() (data fetch) → Environment (data object)

All network calls are avoided; mock repos are loaded from the local filesystem.
"""

import pytest

from interaxions import AutoEnvironment, AutoScaffold, AutoWorkflow
from interaxions.schemas import (
    EnvironmentConfig,
    RuntimeConfig,
    ScaffoldConfig,
    WorkflowConfig,
    XJob,
)
from interaxions.schemas.task import Environment


# ============================================================================
# XJob construction and serialisation
# ============================================================================


@pytest.mark.e2e
class TestXJobConstruction:
    """Full XJob construction and round-trip serialisation."""

    def test_complete_job_construction(self):
        """Build a complete XJob with scaffold, environment, and model in workflow.params."""
        job = XJob(
            name="e2e-swe-bench-job",
            description="End-to-end test job",
            tags=["e2e", "swe-bench"],
            labels={"team": "research", "priority": "high"},
            workflow=WorkflowConfig(
                repo_name_or_path="ix-hub/swe-rollout-verify",
                revision="v1.0.0",
                params={
                    "scaffold": {
                        "repo_name_or_path": "ix-hub/swe-agent",
                        "revision": "v1.0.0",
                        "params": {"max_iterations": 50},
                    },
                    "environment": {
                        "repo_name_or_path": "ix-hub/swe-bench",
                        "id": "astropy__astropy-12907",
                        "params": {"predictions_path": "/tmp/output.jsonl"},
                    },
                    "model": {
                        "type": "litellm",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "sk-test-key",
                    },
                },
            ),
            runtime=RuntimeConfig(
                namespace="experiments",
                service_account="argo-workflow",
                ttl_seconds_after_finished=3600,
            ),
        )

        assert job.job_id is not None
        assert job.name == "e2e-swe-bench-job"
        assert job.workflow.repo_name_or_path == "ix-hub/swe-rollout-verify"
        assert job.runtime.namespace == "experiments"
        params = job.workflow.params
        assert params["scaffold"]["repo_name_or_path"] == "ix-hub/swe-agent"
        assert params["environment"]["id"] == "astropy__astropy-12907"
        assert params["model"]["type"] == "litellm"

    def test_json_round_trip(self, sample_job):
        """XJob can be serialised to JSON and fully restored."""
        json_str = sample_job.model_dump_json()
        restored = XJob.model_validate_json(json_str)

        assert restored.job_id == sample_job.job_id
        assert restored.name == sample_job.name
        assert restored.workflow.repo_name_or_path == sample_job.workflow.repo_name_or_path
        assert restored.workflow.params == sample_job.workflow.params
        assert restored.runtime.namespace == sample_job.runtime.namespace

    def test_dict_round_trip(self, sample_job):
        """XJob can be serialised to a dict and fully restored."""
        data = sample_job.model_dump()
        restored = XJob.model_validate(data)

        assert restored.name == sample_job.name
        assert restored.workflow.params == sample_job.workflow.params

    def test_file_persistence(self, sample_job, tmp_path):
        """XJob survives a write-to-file → read-from-file round trip."""
        job_file = tmp_path / "job.json"
        job_file.write_text(sample_job.model_dump_json(indent=2))

        loaded = XJob.model_validate_json(job_file.read_text())
        assert loaded.name == sample_job.name
        assert loaded.workflow.params == sample_job.workflow.params

    def test_multiple_jobs_have_unique_ids(self, sample_workflow_config, sample_runtime_config):
        """Auto-generated job IDs are unique across instances."""
        ids = {
            XJob(workflow=sample_workflow_config, runtime=sample_runtime_config).job_id
            for _ in range(10)
        }
        assert len(ids) == 10


# ============================================================================
# Component loading from local repos
# ============================================================================


@pytest.mark.e2e
class TestComponentLoading:
    """End-to-end component loading via Auto* classes from local mock repos."""

    def test_load_all_three_components(
        self, mock_scaffold_repo, mock_environment_repo, mock_workflow_repo
    ):
        """All three Auto* classes can load from local repositories."""
        scaffold = AutoScaffold.from_repo(mock_scaffold_repo)
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert scaffold is not None
        assert env_task is not None
        assert workflow is not None

    def test_environment_get_returns_environment(self, mock_environment_repo):
        """Full pipeline: load env executor → call get() → receive Environment."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("django__django-12345")

        assert isinstance(env, Environment)
        assert env.id == "django__django-12345"
        assert env.type == "test-environment"
        assert isinstance(env.data, dict)

    def test_environment_data_accessible_in_workflow(self, mock_environment_repo):
        """Environment.data is accessible after get(), suitable for downstream use."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        env = env_task.get("astropy__astropy-12907")

        # Downstream code (scaffold, workflow) uses env.data["key"]
        assert "instance_id" in env.data
        assert env.data["instance_id"] == "astropy__astropy-12907"

    def test_environment_subclass_pattern(self, mock_environment_repo):
        """Workflow-specific Environment subclass can extend the base Environment."""
        env_task = AutoEnvironment.from_repo(mock_environment_repo)
        base_env = env_task.get("test-123")

        # Simulate what a workflow does: wrap base env in a typed domain object
        class MyWorkflowEnv(Environment):
            fix_hack: bool = False

            @classmethod
            def from_env(cls, env: Environment, fix_hack: bool = False) -> "MyWorkflowEnv":
                return cls(id=env.id, type=env.type, data=env.data, fix_hack=fix_hack)

        typed_env = MyWorkflowEnv.from_env(base_env, fix_hack=True)

        assert isinstance(typed_env, Environment)
        assert typed_env.id == base_env.id
        assert typed_env.data == base_env.data
        assert typed_env.fix_hack is True


# ============================================================================
# XJob + component loading integration
# ============================================================================


@pytest.mark.e2e
class TestJobToComponentPipeline:
    """Tests that simulate real workflow execution patterns."""

    def test_xjob_drives_component_loading(
        self,
        mock_scaffold_repo,
        mock_environment_repo,
        mock_workflow_repo,
        sample_runtime_config,
    ):
        """An XJob's workflow.params can drive AutoScaffold and AutoEnvironment loading."""
        job = XJob(
            workflow=WorkflowConfig(
                repo_name_or_path=str(mock_workflow_repo),
                params={
                    "scaffold": {"repo_name_or_path": str(mock_scaffold_repo), "id": "dummy", "params": {}},
                    "environment": {
                        "repo_name_or_path": str(mock_environment_repo),
                        "id": "django__django-12345",
                        "params": {},
                    },
                },
            ),
            runtime=sample_runtime_config,
        )

        # Parse params (as a real workflow would do)
        scaffold_cfg = ScaffoldConfig(**job.workflow.params["scaffold"])
        env_cfg = EnvironmentConfig(**job.workflow.params["environment"])

        # Load components
        scaffold = AutoScaffold.from_repo(scaffold_cfg.repo_name_or_path)
        env_task = AutoEnvironment.from_repo(env_cfg.repo_name_or_path)
        env = env_task.get(env_cfg.id)

        assert scaffold is not None
        assert env.id == "django__django-12345"
        assert env.type == "test-environment"

    def test_runtime_config_accessible_from_job(self, sample_job):
        """Runtime config fields are correctly accessible from the job."""
        rt = sample_job.runtime
        assert rt.namespace == "experiments"
        assert rt.service_account == "argo-workflow"
        assert rt.ttl_seconds_after_finished == 3600

    def test_workflow_params_deserialized_as_configs(self, sample_job):
        """workflow.params can be deserialized into typed config objects."""
        params = sample_job.workflow.params

        scaffold_cfg = ScaffoldConfig(**params["scaffold"])
        env_cfg = EnvironmentConfig(**params["environment"])

        assert scaffold_cfg.repo_name_or_path == "ix-hub/swe-agent"
        assert env_cfg.id == "astropy__astropy-12907"
        assert isinstance(scaffold_cfg.params, dict)
        assert isinstance(env_cfg.params, dict)

    def test_metadata_tags_and_labels(self):
        """Tags and labels on XJob are preserved through serialisation."""
        job = XJob(
            name="tagged-job",
            tags=["swe-bench", "gpt-4o", "experiment"],
            labels={"team": "research", "env": "staging"},
            workflow=WorkflowConfig(repo_name_or_path="ix-hub/wf", params={}),
            runtime=RuntimeConfig(namespace="staging"),
        )

        data = job.model_dump()
        restored = XJob.model_validate(data)

        assert restored.tags == ["swe-bench", "gpt-4o", "experiment"]
        assert restored.labels["team"] == "research"
        assert restored.labels["env"] == "staging"
