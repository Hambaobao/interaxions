"""
End-to-end tests for the complete Job → Workflow pipeline.
"""

from datetime import datetime
from pathlib import Path

import pytest
from freezegun import freeze_time

from interaxions import AutoWorkflow
from interaxions.schemas import Environment, Job, LiteLLMModel, Runtime, Scaffold, Workflow


@pytest.mark.e2e
class TestJobToWorkflowPipeline:
    """Tests for the complete Job → Workflow creation pipeline."""

    @freeze_time("2025-01-01 12:00:00")
    def test_complete_job_creation(self):
        """Test creating a complete Job with all components."""
        job = Job(
            name="e2e-test-job",
            description="End-to-end test job",
            tags=["e2e", "test"],
            labels={"test_type": "integration"},
            model=LiteLLMModel(
                type="litellm",
                provider="openai",
                model="gpt-4",
            ),
            scaffold=Scaffold(
                repo_name_or_path="swe-agent",
                params={},
            ),
            environment=Environment(
                repo_name_or_path="swe-bench",
                environment_id="django__django-12345",
                source="hf",
                params={
                    "dataset": "princeton-nlp/SWE-bench",
                    "split": "test",
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
        assert job.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert job.model.provider == "openai"
        assert job.scaffold.repo_name_or_path == "swe-agent"
        assert job.environment.source == "hf"
        assert job.workflow.repo_name_or_path == "rollout-and-verify"

    def test_job_serialization_roundtrip(self, sample_job):
        """Test Job serialization and deserialization roundtrip."""
        # Serialize to JSON
        json_str = sample_job.model_dump_json()
        
        # Deserialize from JSON
        restored_job = Job.model_validate_json(json_str)
        
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
        """Test creating a Hera Workflow from a Job."""
        # Mock external dependencies
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
        # Load workflow template
        workflow_template = AutoWorkflow.from_repo(sample_job.workflow.repo_name_or_path)
        
        # Create workflow from job
        workflow = workflow_template.create_workflow(sample_job)
        
        # Verify workflow was created
        assert workflow is not None
        assert hasattr(workflow, "name")
        assert hasattr(workflow, "namespace")

    def test_job_persistence_workflow(self, sample_job, tmp_path: Path, mocker):
        """Test saving Job to file and creating workflow from loaded Job."""
        # Mock external dependencies
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
        # Save Job to file
        job_file = tmp_path / "test_job.json"
        job_file.write_text(sample_job.model_dump_json())
        
        # Load Job from file
        loaded_job = Job.model_validate_json(job_file.read_text())
        
        # Create workflow from loaded job
        workflow_template = AutoWorkflow.from_repo(loaded_job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(loaded_job)
        
        assert workflow is not None
        assert workflow.namespace == loaded_job.runtime.namespace


@pytest.mark.e2e
class TestJobComponentsIntegration:
    """Tests for integration between Job components."""

    def test_job_with_hf_environment(self, sample_model, sample_scaffold, sample_workflow, mocker):
        """Test Job with HuggingFace environment source."""
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
        job = Job(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=Environment(
                repo_name_or_path="swe-bench",
                environment_id="test-hf",
                source="hf",
                params={
                    "dataset": "test-dataset",
                    "split": "test",
                },
            ),
            workflow=sample_workflow,
        )
        
        workflow_template = AutoWorkflow.from_repo(job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(job)
        
        assert workflow is not None

    def test_job_with_oss_environment(self, sample_model, sample_scaffold, sample_workflow, mocker):
        """Test Job with OSS environment source."""
        mock_oss = mocker.patch("ossdata.Dataset.load")
        mock_oss.return_value = []
        
        job = Job(
            model=sample_model,
            scaffold=sample_scaffold,
            environment=Environment(
                repo_name_or_path="swe-bench",
                environment_id="test-oss",
                source="oss",
                params={
                    "dataset": "test-dataset",
                    "split": "test",
                    "oss_region": "cn-hangzhou",
                    "oss_endpoint": "oss-cn-hangzhou.aliyuncs.com",
                    "oss_access_key_id": "test",
                    "oss_access_key_secret": "test",
                },
            ),
            workflow=sample_workflow,
        )
        
        workflow_template = AutoWorkflow.from_repo(job.workflow.repo_name_or_path)
        workflow = workflow_template.create_workflow(job)
        
        assert workflow is not None

    def test_job_runtime_configuration(self, sample_job, mocker):
        """Test that Job runtime configuration is used in workflow."""
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
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
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
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
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
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
        """Test modifying a Job and recreating workflow."""
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
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
        """Test Job with custom tags and labels."""
        mock_datasets = mocker.patch("datasets.load_dataset")
        mock_datasets.return_value = mocker.MagicMock()
        
        job = Job(
            name="custom-job",
            tags=["custom", "test", "e2e"],
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

