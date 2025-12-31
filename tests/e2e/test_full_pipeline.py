"""
End-to-end tests for the complete XJob → Workflow pipeline.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time

from interaxions import AutoWorkflow
from interaxions.schemas import Environment, XJob, LiteLLMModel, Runtime, Scaffold, Workflow
from interaxions.schemas.environment import HFEEnvironmentSource, OSSEnvironmentSource

# Check if ossdata is available
try:
    import ossdata
    HAS_OSSDATA = True
except ImportError:
    HAS_OSSDATA = False


@pytest.mark.e2e
class TestJobToWorkflowPipeline:
    """Tests for the complete XJob → Workflow creation pipeline."""

    def test_complete_job_creation(self):
        """Test creating a complete XJob with all components."""
        job = XJob(
            name="e2e-test-job",
            description="End-to-end test job",
            tags=["e2e", "test"],
            labels={"test_type": "integration"},
            model=LiteLLMModel(
                type="litellm",
                provider="openai",
                model="gpt-4",
                base_url="https://api.openai.com/v1",
                api_key="sk-test-key",
            ),
            scaffold=Scaffold(
                repo_name_or_path="swe-agent",
                params={},
            ),
            environment=Environment(
                repo_name_or_path="swe-bench",
                environment_id="astropy__astropy-12907",
                source=HFEEnvironmentSource(
                    dataset="princeton-nlp/SWE-bench",
                    split="test",
                ),
                extra_params={
                    "predictions_path": "gold",
                },
            ),
            workflow=Workflow(
                repo_name_or_path="rollout-and-verify",
                params={},
            ),
            runtime=Runtime(
                namespace="e2e-tests",
                service_account="test-account",
            ),
        )

        assert job.job_id is not None
        assert job.name == "e2e-test-job"
        assert job.model.provider == "openai"
        assert job.scaffold.repo_name_or_path == "swe-agent"
        assert job.environment.source.type == "hf"
        assert job.workflow.repo_name_or_path == "rollout-and-verify"

    def test_job_serialization_roundtrip(self, sample_job):
        """Test XJob serialization and deserialization roundtrip."""
        # Serialize to JSON
        json_str = sample_job.model_dump_json()

        # Deserialize from JSON
        restored_job = XJob.model_validate_json(json_str)

        # Verify all fields match
        assert restored_job.name == sample_job.name
        assert restored_job.description == sample_job.description
        assert restored_job.tags == sample_job.tags
        assert restored_job.labels == sample_job.labels
        assert restored_job.model.provider == sample_job.model.provider
        assert restored_job.scaffold.repo_name_or_path == sample_job.scaffold.repo_name_or_path
        assert restored_job.environment.environment_id == sample_job.environment.environment_id
        assert restored_job.workflow.repo_name_or_path == sample_job.workflow.repo_name_or_path

    def test_job_to_workflow_creation(self, sample_job, mocker):
        """Test creating a Hera Workflow from an XJob."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "astropy__astropy-12907",
            "repo": "astropy/astropy",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        # Load workflow template
        workflow_template = AutoWorkflow.from_repo(sample_job.workflow.repo_name_or_path)

        # Create workflow from job
        workflow = workflow_template.create_workflow(sample_job)

        # Verify workflow was created
        assert workflow is not None
        assert hasattr(workflow, "name")
        assert hasattr(workflow, "namespace")

    def test_job_persistence_workflow(self, sample_job, tmp_path: Path, mocker):
        """Test saving XJob to file and creating workflow from loaded XJob."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "astropy__astropy-12907",
            "repo": "astropy/astropy",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        # Save XJob to file
        job_file = tmp_path / "test_job.json"
        job_file.write_text(sample_job.model_dump_json())

        # Load XJob from file
        loaded_job = XJob.model_validate_json(job_file.read_text())

        # Create workflow from loaded job
        workflow_template = AutoWorkflow.from_repo(loaded_job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(loaded_job)

        assert workflow is not None
        assert workflow.namespace == loaded_job.runtime.namespace


@pytest.mark.e2e
class TestJobComponentsIntegration:
    """Tests for integration between XJob components."""

    def test_job_with_hf_environment(self, sample_model, sample_scaffold, sample_workflow, mocker):
        """Test XJob with HuggingFace environment source."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "test-hf",
            "repo": "test/repo",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        job = XJob(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=Environment(
                repo_name_or_path="swe-bench",
                environment_id="test-hf",
                source=HFEEnvironmentSource(
                    dataset="test-dataset",
                    split="test",
                ),
            ),
            workflow=sample_workflow,
            runtime=Runtime(
                namespace="test-namespace",
                service_account="test-sa",
            ),
        )

        workflow_template = AutoWorkflow.from_repo(job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(job)

        assert workflow is not None

    @pytest.mark.skipif(not HAS_OSSDATA, reason="ossdata is optional dependency")
    def test_job_with_oss_environment(self, sample_model, sample_scaffold, sample_workflow, mocker):
        """Test XJob with OSS environment source."""
        pytest.importorskip("ossdata")
        mock_item = {
            "instance_id": "test-oss",
            "repo": "test/repo",
            "base_commit": "abc123",
            "problem_statement": "test problem",
            "docker_image": "swe-bench:test-oss",
        }
        mock_oss = mocker.patch("ossdata.get_item")
        mock_oss.return_value = json.dumps(mock_item)

        job = XJob(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=Environment(
                repo_name_or_path="swe-bench",
                environment_id="test-oss",
                source=OSSEnvironmentSource(
                    dataset="test-dataset",
                    split="test",
                    oss_region="cn-hangzhou",
                    oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
                    oss_access_key_id="test",
                    oss_access_key_secret="test",
                ),
            ),
            workflow=sample_workflow,
            runtime=Runtime(namespace="test-namespace"),
        )

        workflow_template = AutoWorkflow.from_repo(job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(job)

        assert workflow is not None

    def test_job_runtime_configuration(self, sample_job, mocker):
        """Test that XJob runtime configuration is used in workflow."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "astropy__astropy-12907",
            "repo": "astropy/astropy",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        # Update runtime configuration
        sample_job.runtime.namespace = "custom-namespace"
        sample_job.runtime.service_account = "custom-sa"

        workflow_template = AutoWorkflow.from_repo(sample_job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(sample_job)

        assert workflow.namespace == "custom-namespace"


@pytest.mark.e2e
@pytest.mark.slow
class TestWorkflowExecution:
    """Tests for workflow execution (slow tests)."""

    def test_workflow_yaml_generation(self, sample_job, mocker):
        """Test that workflow can generate YAML."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "astropy__astropy-12907",
            "repo": "astropy/astropy",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        workflow_template = AutoWorkflow.from_repo(sample_job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(sample_job)

        # Generate YAML (doesn't require cluster)
        yaml_str = workflow.to_yaml()

        assert yaml_str is not None
        assert isinstance(yaml_str, str)
        assert len(yaml_str) > 0
        assert "apiVersion" in yaml_str or "kind" in yaml_str

    def test_workflow_has_required_fields(self, sample_job, mocker):
        """Test that generated workflow has all required Argo fields."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "astropy__astropy-12907",
            "repo": "astropy/astropy",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        workflow_template = AutoWorkflow.from_repo(sample_job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(sample_job)

        # Check workflow structure
        assert hasattr(workflow, "name")
        assert hasattr(workflow, "namespace")
        assert workflow.name is not None
        assert workflow.namespace is not None


@pytest.mark.e2e
class TestJobModification:
    """Tests for modifying Jobs and recreating workflows."""

    def test_modify_job_and_recreate_workflow(self, sample_job, mocker):
        """Test modifying an XJob and recreating workflow."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "astropy__astropy-12907",
            "repo": "astropy/astropy",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        # Create initial workflow
        workflow_template = AutoWorkflow.from_repo(sample_job.workflow.repo_name_or_path)
        workflow1 = workflow_template.create_workflow(sample_job)
        original_namespace = workflow1.namespace

        # Modify job
        sample_job.runtime.namespace = "modified-namespace"
        sample_job.environment.environment_id = "modified-env-123"

        # Recreate workflow with modified job
        workflow2 = workflow_template.create_workflow(sample_job)

        # Verify changes are reflected
        assert workflow2.namespace == "modified-namespace"
        assert workflow2.namespace != original_namespace

    def test_job_with_custom_tags_and_labels(self, sample_model, sample_scaffold, sample_environment, sample_workflow, mocker):
        """Test XJob with custom tags and labels."""
        # Mock external dependencies - HuggingFace datasets
        mock_item = {
            "instance_id": "astropy__astropy-12907",
            "repo": "astropy/astropy",
            "base_commit": "abc123",
            "problem_statement": "Test problem",
            "hints_text": "",
            "created_at": "2023-01-01",
            "patch": "diff --git a/test.py b/test.py\n",
            "test_patch": "diff --git a/test_test.py b/test_test.py\n",
            "version": "1.0",
            "FAIL_TO_PASS": '["test_pass"]',
            "PASS_TO_PASS": '["test_existing"]',
            "environment_setup_commit": "def456",
        }
        mock_filtered = mocker.MagicMock()
        mock_filtered.__len__ = mocker.MagicMock(return_value=1)
        mock_filtered.__getitem__ = mocker.MagicMock(return_value=mock_item)

        mock_dataset = mocker.MagicMock()
        mock_dataset.filter = mocker.MagicMock(return_value=mock_filtered)

        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mock_dataset

        job = XJob(
            name="custom-job",
            tags=["custom", "test", "e2e"],
            runtime=Runtime(
                namespace="test-namespace",
                service_account="test-sa",
            ),
            labels={
                "team": "research",
                "priority": "high",
                "project": "interaxions",
            },
            model=sample_model,
            scaffold=sample_scaffold,
            environment=sample_environment,
            workflow=sample_workflow,
        )

        # Verify job metadata
        assert len(job.tags) == 3
        assert job.labels["team"] == "research"
        assert job.labels["priority"] == "high"

        # Create workflow
        workflow_template = AutoWorkflow.from_repo(job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(job)

        assert workflow is not None
