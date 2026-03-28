"""
End-to-end tests for the complete Job → component loading pipeline.

These tests exercise the full flow:
  Job (schema) → AutoWorkflow / AutoTask (loading) → Argo Workflow

All network calls are avoided; mock repos are loaded from the local filesystem.
"""

import pytest

from interaxions import AutoWorkflow, AutoTask
from interaxions.schemas import (
    Job,
    RuntimeConfig,
    WorkflowConfig,
)


# ============================================================================
# Job construction and serialisation
# ============================================================================


@pytest.mark.e2e
class TestJobConstruction:
    """Full Job construction and round-trip serialisation."""

    def test_complete_job_construction(self):
        """Build a complete Job with task configs in workflow.params."""
        job = Job(
            name="e2e-swe-bench-job",
            description="End-to-end test job",
            tags=["e2e", "swe-bench"],
            labels={"team": "research", "priority": "high"},
            workflow=WorkflowConfig(
                repo_name_or_path="ix-hub/swe-rollout-verify",
                revision="v1.0.0",
                params={
                    "instance_id": "astropy__astropy-12907",
                    "agent": {
                        "repo_name_or_path": "ix-hub/swe-agent",
                        "revision": "v1.0.0",
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
        assert params["instance_id"] == "astropy__astropy-12907"
        assert params["agent"]["repo_name_or_path"] == "ix-hub/swe-agent"
        assert params["model"]["type"] == "litellm"

    def test_json_round_trip(self, sample_job):
        """Job can be serialised to JSON and fully restored."""
        json_str = sample_job.model_dump_json()
        restored = Job.model_validate_json(json_str)

        assert restored.job_id == sample_job.job_id
        assert restored.name == sample_job.name
        assert restored.workflow.repo_name_or_path == sample_job.workflow.repo_name_or_path
        assert restored.workflow.params == sample_job.workflow.params
        assert restored.runtime.namespace == sample_job.runtime.namespace

    def test_dict_round_trip(self, sample_job):
        """Job can be serialised to a dict and fully restored."""
        data = sample_job.model_dump()
        restored = Job.model_validate(data)

        assert restored.name == sample_job.name
        assert restored.workflow.params == sample_job.workflow.params

    def test_file_persistence(self, sample_job, tmp_path):
        """Job survives a write-to-file → read-from-file round trip."""
        job_file = tmp_path / "job.json"
        job_file.write_text(sample_job.model_dump_json(indent=2))

        loaded = Job.model_validate_json(job_file.read_text())
        assert loaded.name == sample_job.name
        assert loaded.workflow.params == sample_job.workflow.params

    def test_multiple_jobs_have_unique_ids(self, sample_workflow_config, sample_runtime_config):
        """Auto-generated job IDs are unique across instances."""
        ids = {
            Job(workflow=sample_workflow_config, runtime=sample_runtime_config).job_id
            for _ in range(10)
        }
        assert len(ids) == 10


# ============================================================================
# Component loading from local repos
# ============================================================================


@pytest.mark.e2e
class TestComponentLoading:
    """End-to-end component loading via Auto* classes from local mock repos."""

    def test_load_workflow_and_task(self, mock_workflow_repo, mock_task_repo):
        """AutoWorkflow and AutoTask can both load from local repositories."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)
        task = AutoTask.from_repo(mock_task_repo)

        assert workflow is not None
        assert task is not None

    def test_task_has_create_task_method(self, mock_task_repo):
        """Loaded task exposes a callable create_task() method."""
        task = AutoTask.from_repo(mock_task_repo)

        assert hasattr(task, "create_task")
        assert callable(task.create_task)

    def test_workflow_has_create_workflow_method(self, mock_workflow_repo):
        """Loaded workflow exposes a callable create_workflow() method."""
        workflow = AutoWorkflow.from_repo(mock_workflow_repo)

        assert hasattr(workflow, "create_workflow")
        assert callable(workflow.create_workflow)


# ============================================================================
# Job + component loading integration
# ============================================================================


@pytest.mark.e2e
class TestJobToComponentPipeline:
    """Tests that simulate real workflow execution patterns."""

    def test_job_params_drive_task_loading(
        self,
        mock_task_repo,
        mock_workflow_repo,
        sample_runtime_config,
    ):
        """A Job's workflow.params can drive AutoTask loading."""
        job = Job(
            workflow=WorkflowConfig(
                repo_name_or_path=str(mock_workflow_repo),
                params={
                    "instance_id": "django__django-12345",
                    "agent": {"repo_name_or_path": str(mock_task_repo)},
                },
            ),
            runtime=sample_runtime_config,
        )

        # 模拟 workflow 内部根据 params 加载 task
        agent_repo = job.workflow.params["agent"]["repo_name_or_path"]
        task = AutoTask.from_repo(agent_repo)

        assert task is not None
        assert job.workflow.params["instance_id"] == "django__django-12345"

    def test_runtime_config_accessible_from_job(self, sample_job):
        """Runtime config fields are correctly accessible from the job."""
        rt = sample_job.runtime
        assert rt.namespace == "experiments"
        assert rt.service_account == "argo-workflow"
        assert rt.ttl_seconds_after_finished == 3600

    def test_metadata_tags_and_labels(self):
        """Tags and labels on Job are preserved through serialisation."""
        job = Job(
            name="tagged-job",
            tags=["swe-bench", "gpt-4o", "experiment"],
            labels={"team": "research", "env": "staging"},
            workflow=WorkflowConfig(repo_name_or_path="ix-hub/wf", params={}),
            runtime=RuntimeConfig(namespace="staging"),
        )

        data = job.model_dump()
        restored = Job.model_validate(data)

        assert restored.tags == ["swe-bench", "gpt-4o", "experiment"]
        assert restored.labels["team"] == "research"
        assert restored.labels["env"] == "staging"
