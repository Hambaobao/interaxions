"""
Sample data for testing.
"""

from interaxions.schemas import Environment, XJob, LiteLLMModel, Runtime, Scaffold, Workflow
from interaxions.schemas.environment import HFEEnvironmentSource, OSSEnvironmentSource


def create_sample_model() -> LiteLLMModel:
    """Create a sample model for testing."""
    return LiteLLMModel(
        type="litellm",
        provider="openai",
        model="gpt-4",
        base_url="https://api.openai.com/v1",
        api_key="sk-test-key",
        temperature=0.7,
    )


def create_sample_scaffold() -> Scaffold:
    """Create a sample scaffold for testing."""
    return Scaffold(
        repo_name_or_path="swe-agent",
        extra_params={
            "max_iterations": 10,
            "config": "default.yaml",
        },
    )


def create_sample_environment_hf() -> Environment:
    """Create a sample HF environment for testing."""
    return Environment(
        repo_name_or_path="swe-bench",
        environment_id="astropy__astropy-12907",
        source=HFEEnvironmentSource(
            dataset="princeton-nlp/SWE-bench",
            split="test",
        ),
        extra_params={
            "predictions_path": "gold",
        },
    )


def create_sample_environment_oss() -> Environment:
    """Create a sample OSS environment for testing."""
    return Environment(
        repo_name_or_path="swe-bench",
        environment_id="astropy__astropy-12907",
        source=OSSEnvironmentSource(
            dataset="swe-bench",
            split="test",
            oss_region="cn-hangzhou",
            oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
            oss_access_key_id="test-key",
            oss_access_key_secret="test-secret",
        ),
        extra_params={
            "predictions_path": "gold",
        },
    )


def create_sample_workflow() -> Workflow:
    """Create a sample workflow for testing."""
    return Workflow(
        repo_name_or_path="rollout-and-verify",
        params={},
    )


def create_sample_runtime() -> Runtime:
    """Create a sample runtime for testing."""
    return Runtime(
        namespace="test-namespace",
        service_account="test-account",
        ttl_seconds_after_finished=3600,
        extra_params={
            "labels": {"test": "true"},
        },
    )


def create_sample_job() -> XJob:
    """Create a complete sample XJob for testing."""
    return XJob(
        name="test-job",
        description="A test job",
        tags=["test", "sample"],
        labels={"type": "test"},
        model=create_sample_model(),
        scaffold=create_sample_scaffold(),
        environment=create_sample_environment_hf(),
        workflow=create_sample_workflow(),
        runtime=create_sample_runtime(),
    )


# Sample configurations as dictionaries
SAMPLE_SCAFFOLD_CONFIG = {
    "type": "test-scaffold",
    "param1": "value1",
    "param2": 42,
}

SAMPLE_ENVIRONMENT_CONFIG = {
    "type": "test-environment",
    "source": "hf",
}

SAMPLE_WORKFLOW_CONFIG = {
    "type": "test-workflow",
}

# Sample XJob as dictionary
SAMPLE_JOB_DICT = {
    "name": "test-job-dict",
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
        "source": {
            "type": "hf",
            "dataset": "test-dataset",
            "split": "test",
        },
        "extra_params": {},
    },
    "workflow": {
        "repo_name_or_path": "rollout-and-verify",
        "params": {},
    },
    "runtime": {
        "namespace": "default",
    },
}

