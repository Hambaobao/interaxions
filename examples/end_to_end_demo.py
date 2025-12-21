#!/usr/bin/env python3
"""
End-to-end example: Loading agent and environment, creating tasks

This example shows the complete workflow from loading to task creation.
"""

from interaxions import AutoAgent, AutoEnvironmentFactory

print("=" * 70)
print("End-to-End Example")
print("=" * 70)
print()

# Step 1: Load agent
print("Step 1: Load agent")
agent = AutoAgent.from_repo("swe-agent")
print(f"  ✓ Agent: {agent.__class__.__name__}")
print()

# Step 2: Load environment factory  
print("Step 2: Load environment factory")
env_factory = AutoEnvironmentFactory.from_repo("swe-bench")
print(f"  ✓ Factory: {env_factory.__class__.__name__}")
print()

# Step 3: Get environment instance (example)
print("Step 3: Get environment instance")
print("  Note: This requires actual data source configuration")
print("  Example methods:")
print("    - env_factory.get_from_oss(bucket, key, region)")
print("    - env_factory.get_from_hf(dataset, split, instance_id)")
print()

# Step 4: Create task (example)
print("Step 4: Create task")
print("  When you have an environment instance:")
print("    task = agent.create_task(")
print("        name='solve-issue',")
print("        env=env,")
print("        max_iterations=10,")
print("        model='gpt-4'")
print("    )")
print()

print("=" * 70)
print("✅ Example complete")
print("=" * 70)
print()
print("To run with real data:")
print("  1. Configure OSS/HuggingFace credentials")
print("  2. Get environment instance from factory")
print("  3. Create and execute task")
