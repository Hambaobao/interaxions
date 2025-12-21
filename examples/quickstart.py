#!/usr/bin/env python3
"""
End-to-End Tutorial: Building a Complete Workflow

This tutorial demonstrates the complete workflow of using Interaxions:
- Three-layer abstraction: Agent, Environment, Workflow
- Dynamic loading with Auto classes
- Creating and orchestrating Argo Workflows

Follow along by reading the code and comments below.
"""

from interaxions import AutoAgent, AutoEnvironmentFactory, AutoWorkflow


def main():
    """
    Complete tutorial showing how to build an end-to-end workflow.
    
    The workflow follows this pattern:
    1. Agent receives a task and generates a solution
    2. Environment verifies the solution and reports results
    """

    # ============================================================================
    # STEP 1: Load Agent
    # ============================================================================
    # Agents solve problems (e.g., write code, fix bugs, answer questions)
    # They are configurable with different models, prompts, and tools

    agent = AutoAgent.from_repo("swe-agent")
    print(f"✓ Loaded agent: {type(agent).__name__}")

    # The agent can be loaded from:
    # - Built-in: AutoAgent.from_repo("swe-agent")
    # - Remote: AutoAgent.from_repo("username/custom-agent")
    # - Local: AutoAgent.from_repo("./my-agent")
    # - Versioned: AutoAgent.from_repo("user/agent", revision="v1.0.0")

    # ============================================================================
    # STEP 2: Load Environment Factory
    # ============================================================================
    # Environments evaluate solutions by running tests and checks
    # A factory creates environment instances for specific tasks

    env_factory = AutoEnvironmentFactory.from_repo("swe-bench")
    print(f"✓ Loaded environment factory: {type(env_factory).__name__}")

    # Environment factories provide methods to get specific instances:
    # - From HuggingFace: env_factory.get_from_hf(...)
    # - From OSS: env_factory.get_from_oss(...)

    # ============================================================================
    # STEP 3: Create Environment Instance (Example)
    # ============================================================================
    # To create a real workflow, first get an environment instance

    # Option A: Load from HuggingFace dataset
    env = env_factory.get_from_hf(
        environment_id="astropy__astropy-12907",
        dataset="princeton-nlp/SWE-bench_Verified",
        split="test",
    )

    # Option B: Load from OSS (Aliyun Object Storage)
    # env = env_factory.get_from_oss(
    #     environment_id="astropy__astropy-12907",
    #     dataset="princeton-nlp/SWE-bench_Verified",
    #     split="test",
    #     oss_region="cn-hangzhou",
    #     oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
    #     oss_access_key_id="your-key-id",
    #     oss_access_key_secret="your-secret-key",
    # )

    print("\nℹ️  Environment instance creation requires actual data sources")
    print("   Uncomment one of the options above to use with real data")

    # ============================================================================
    # STEP 4: Load Workflow Template
    # ============================================================================
    # Workflows orchestrate agents and environments into Argo Workflows
    # They define task dependencies and execution order

    workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
    print(f"✓ Loaded workflow: {type(workflow_template).__name__}")

    # This workflow creates two tasks:
    #   Agent Rollout → Environment Verify
    #
    # Tasks run in separate containers and communicate via Argo artifacts

    # ============================================================================
    # STEP 5: Create Workflow (Example)
    # ============================================================================
    # With an environment instance, create the workflow

    workflow = workflow_template.create_workflow(
        name="solve-astropy-issue",
        agent=agent,
        environment=env,
        namespace="default",
    )

    print("\n" + "=" * 70)
    print("Tutorial complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
