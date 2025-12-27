#!/usr/bin/env python3
"""
Interaxions Framework - Complete Tutorial

This tutorial demonstrates the complete workflow for running AI agents in Kubernetes:
1. Define an XJob with all configurations (model, scaffold, environment, workflow)
2. Serialize/deserialize XJob for storage or transmission
3. Create an Argo Workflow from the XJob
4. Submit to Kubernetes or export as YAML

The XJob protocol is the unified contract that defines how all components interact.

FLEXIBLE COMPOSITION:
XJob components are fully composable - you can mix and match as needed:
- XJob() - Empty job, only metadata (job_id auto-generated)
- XJob(model=..., scaffold=...) - Simple agent run
- XJob(environment=...) - Dataset access only
- XJob(model=..., scaffold=..., environment=...) - Agent evaluation
- XJob(...all...) - Full workflow orchestration (as shown below)

This tutorial shows the FULL configuration. See end of file for simplified examples.
"""

from pathlib import Path

from interaxions.hub import AutoWorkflow
from interaxions.schemas import (
    Environment,
    XJob,
    LiteLLMModel,
    Runtime,
    Scaffold,
    Workflow,
)


def main():
    """Complete tutorial: from XJob definition to Workflow creation."""

    print("=" * 80)
    print("Interaxions Framework - Complete Tutorial")
    print("=" * 80)

    # ==========================================================================
    # Step 1: Define an XJob
    # ==========================================================================
    # The XJob encapsulates all configuration needed for a single task execution:
    # - Model: Which LLM to use (via LiteLLM)
    # - Scaffold: Which agent implementation to use
    # - Environment: Which environment/dataset to work with
    # - Workflow: How to orchestrate the agent and environment
    # - Runtime: Kubernetes/Argo runtime settings

    print("\n1. Defining XJob specification...")

    job = XJob(
        # XJob metadata (auto-generated if not provided)
        name="astropy-fix-demo",
        description="Demonstrate fixing Astropy issue using SWE-Agent",
        tags=["tutorial", "swe-bench", "astropy", "bugfix"],
        labels={
            "team": "research",
            "project": "astropy",
            "priority": "high"
        },

        # Model configuration - using LiteLLM for unified API
        model=LiteLLMModel(
            type="litellm",  # Discriminator field for Pydantic
            provider="openai",
            model="gpt-4",
            api_key="sk-your-api-key-here",  # Replace with actual key or use env var
            base_url="https://api.openai.com/v1",
            temperature=0.7,
            num_retries=3,
        ),

        # Scaffold configuration - defines the agent behavior
        # The scaffold can internally manage single or multiple agents
        scaffold=Scaffold(
            repo_name_or_path="swe-agent",  # Built-in, or use "username/repo" or "./path"
            revision=None,  # None = use repository default branch
            params={
                # Scaffold-specific parameters
                "sweagent_config": "default.yaml",
                "tools_parse_function": "python",
                "max_iterations": 10,
                "max_observation_length": 1000,
            }),

        # Environment configuration - defines where the agent operates
        environment=Environment(
            repo_name_or_path="swe-bench",
            revision=None,
            environment_id="astropy__astropy-12907",  # Specific task instance
            source="hf",  # Data source: "hf" (HuggingFace), "oss" (Object Storage), or custom
            params={
                # Data source parameters
                "dataset": "princeton-nlp/SWE-bench_Verified",
                "split": "test",
                # Task parameters
                "predictions_path": "/workspace/predictions.json"
            }),

        # Workflow configuration - defines orchestration logic
        workflow=Workflow(
            repo_name_or_path="rollout-and-verify",  # Sequential: agent rollout → env verify
            revision=None,
            params={}  # Workflow-specific parameters if needed
        ),

        # Runtime configuration - Kubernetes/Argo settings
        runtime=Runtime(
            namespace="experiments",
            service_account="argo-workflow",
            image_pull_secrets=["docker-registry-secret"],
            ttl_seconds_after_finished=3600,  # Auto-cleanup after 1 hour
            extra_params={
                # Additional Kubernetes/Argo configurations
                "labels": {
                    "team": "research",
                    "project": "swe-bench"
                },
                "annotations": {
                    "description": "Astropy bug fix experiment"
                },
                "priority_class_name": "high-priority"
            }))

    print("✓ XJob defined")
    print(f"  • XJob ID: {job.job_id}")
    print(f"  • Name: {job.name}")
    print(f"  • Model: {job.model.provider}/{job.model.model}")
    print(f"  • Scaffold: {job.scaffold.repo_name_or_path}")
    print(f"  • Environment: {job.environment.environment_id}")
    print(f"  • Workflow: {job.workflow.repo_name_or_path}")
    print(f"  • Runtime: {job.runtime.namespace}")

    # ==========================================================================
    # Step 2: Serialize XJob (for storage, transmission, or version control)
    # ==========================================================================
    # XJobs can be serialized to JSON for:
    # - Storing in database
    # - Sending via API
    # - Committing to git for reproducibility
    # - Queueing in message brokers

    print("\n2. Serializing XJob...")

    job_json = job.model_dump_json(indent=4)
    output_path = Path("tmp/job.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(job_json)

    print(f"✓ XJob serialized to {output_path}")
    print(f"  • Size: {len(job_json)} bytes")
    print(f"  • Format: JSON (Pydantic model)")

    # ==========================================================================
    # Step 3: Deserialize XJob (simulate loading from storage)
    # ==========================================================================
    # In a real scenario, you might load this from a database, API, or file

    print("\n3. Deserializing XJob (simulating reload)...")

    loaded_json = output_path.read_text()
    loaded_job = XJob.model_validate_json(loaded_json)

    print("✓ XJob deserialized successfully")
    print(f"  • Loaded job ID: {loaded_job.job_id}")
    print(f"  • Validation: Passed (Pydantic strict mode)")

    # ==========================================================================
    # Step 4: Create Workflow from XJob
    # ==========================================================================
    # The workflow template loads the scaffold and environment internally
    # based on the XJob specification, then orchestrates them

    print("\n4. Creating Argo Workflow from XJob...")

    # Load the workflow template specified in the XJob
    workflow_template = AutoWorkflow.from_repo(
        loaded_job.workflow.repo_name_or_path,
        revision=loaded_job.workflow.revision,
        username=loaded_job.workflow.username,
        token=loaded_job.workflow.token,
    )
    print(f"  • Loaded workflow template: {workflow_template.__class__.__name__}")

    # Create the workflow - this internally:
    # 1. Loads the scaffold from job.scaffold.repo_name_or_path
    # 2. Loads the environment from job.environment.repo_name_or_path
    # 3. Creates agent task by calling scaffold.create_task(job)
    # 4. Creates environment task by calling environment.create_task(job)
    # 5. Orchestrates them according to workflow logic
    try:
        workflow = workflow_template.create_workflow(loaded_job)
        print(f"✓ Workflow created: {workflow.name}")

        # Workflow details
        print(f"\n5. Workflow details:")
        print(f"  • Name: {workflow.name} (auto-generated from environment_id)")
        print(f"  • Namespace: {loaded_job.runtime.namespace}")
        print(f"  • Service Account: {loaded_job.runtime.service_account}")
        print(f"  • TTL: {loaded_job.runtime.ttl_seconds_after_finished}s")
        print(f"\n  • Tasks:")
        print(f"    - Agent task: sweagent-{loaded_job.environment.environment_id}")
        print(f"    - Environment task: env-{loaded_job.environment.environment_id}")
        print(f"    - Dependencies: agent → environment (sequential)")

        # ==========================================================================
        # Step 5: Next Steps
        # ==========================================================================
        print("\n" + "=" * 80)
        print("Next Steps")
        print("=" * 80)

        print("\n• To submit this workflow to Argo:")
        print("    workflow.create()")

        print("\n• To export as YAML for inspection or CI/CD:")
        print("    yaml_content = workflow.to_yaml()")
        print("    Path('workflow.yaml').write_text(yaml_content)")

        print("\n• To load different versions:")
        print("    agent = AutoScaffold.from_repo('username/custom-agent', revision='v1.2.0')")
        print("    env = AutoEnvironmentFactory.from_repo('./local-env')")

        print("\n• To customize XJob dynamically:")
        print("    job.model.temperature = 0.9  # Adjust LLM temperature")
        print("    job.scaffold.params['max_iterations'] = 20  # More iterations")
        print("    workflow = workflow_template.create_workflow(job)  # Recreate")

        print("\n" + "=" * 80)
        print("✅ Tutorial Complete!")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("  1. XJob is the unified contract defining all task configurations")
        print("  2. Components are dynamically loaded from built-in/local/remote repos")
        print("  3. Workflows orchestrate scaffolds and environments on Kubernetes")
        print("  4. Everything is serializable, versionable, and reproducible")

        return 0

    except Exception as e:
        print(f"\n❌ Error creating workflow: {e}")
        print("\nNote: This tutorial requires network access for dynamic loading.")
        print("The XJob protocol itself is successfully created and can be:")
        print("  • Serialized to JSON ✓")
        print("  • Stored in database ✓")
        print("  • Sent via API ✓")
        print("  • Validated with Pydantic ✓")

        print("\nTo run with actual execution, ensure:")
        print("  1. Network access to load components")
        print("  2. Valid API keys for LLM providers")
        print("  3. Access to data sources (HuggingFace, OSS, etc.)")
        print("  4. Kubernetes cluster with Argo Workflows installed")

        return 1


# ==========================================================================
# SIMPLIFIED EXAMPLES - Flexible XJob Composition
# ==========================================================================
# Uncomment and modify these examples to see different XJob configurations:

def example_minimal_job():
    """Minimal job - only metadata."""
    from interaxions.schemas import XJob
    
    job = XJob(name="minimal-job")
    # All components are None - useful for testing or placeholders
    print(f"XJob ID: {job.job_id}")
    print(f"Components: model={job.model}, scaffold={job.scaffold}")


def example_scaffold_only():
    """XJob with only scaffold - simple agent run."""
    from interaxions.schemas import XJob, Scaffold, LiteLLMModel
    
    job = XJob(
        name="scaffold-only",
        model=LiteLLMModel(
            provider="openai",
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="your-key"
        ),
        scaffold=Scaffold(
            repo_name_or_path="swe-agent",
            params={"max_iterations": 5}
        )
    )
    # No environment, workflow, or runtime - quick prototyping


def example_environment_only():
    """XJob with only environment - dataset access."""
    from interaxions.schemas import XJob, Environment
    
    job = XJob(
        name="dataset-exploration",
        environment=Environment(
            repo_name_or_path="swe-bench",
            environment_id="django__django-12345",
            source="hf",
            params={
                "dataset": "princeton-nlp/SWE-bench",
                "split": "test"
            }
        )
    )
    # Useful for dataset analysis without running agents


def example_scaffold_and_environment():
    """XJob with scaffold + environment - evaluation without complex workflow."""
    from interaxions.schemas import XJob, Scaffold, Environment, LiteLLMModel
    
    job = XJob(
        name="simple-eval",
        model=LiteLLMModel(
            provider="openai",
            model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key="your-key"
        ),
        scaffold=Scaffold(repo_name_or_path="swe-agent"),
        environment=Environment(
            repo_name_or_path="swe-bench",
            environment_id="test-instance",
            source="hf",
            params={"dataset": "princeton-nlp/SWE-bench", "split": "test"}
        )
    )
    # No workflow or runtime - user handles orchestration


if __name__ == "__main__":
    exit(main())
