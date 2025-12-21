#!/usr/bin/env python3
"""
Quickstart example for Interaxions

Demonstrates basic usage of dynamic loading system.
"""

from interaxions import AutoAgent, AutoEnvironmentFactory

print("=" * 70)
print("Interaxions Quickstart")
print("=" * 70)
print()

# 1. Load builtin agent
print("1. Loading builtin agent...")
agent = AutoAgent.from_repo("swe-agent")
print(f"   ✓ Loaded: {agent.__class__.__name__}")
print(f"   ✓ Type: {agent.config.type}")
print(f"   ✓ Image: {agent.config.image}")
print()

# 2. Load builtin environment factory
print("2. Loading builtin environment factory...")
env_factory = AutoEnvironmentFactory.from_repo("swe-bench")
print(f"   ✓ Loaded: {env_factory.__class__.__name__}")
print(f"   ✓ Type: {env_factory.config.type}")
print()

# 3. Load from local repository (if exists)
print("3. Loading from local repository...")
try:
    local_agent = AutoAgent.from_repo("ix-hub/swe-agent-lite")
    print(f"   ✓ Loaded: {local_agent.__class__.__name__}")
    print(f"   ✓ Type: {local_agent.config.type}")
except Exception as e:
    print(f"   ⚠ Skipped: {e}")
print()

# 4. Load with version
print("4. Loading specific version...")
try:
    versioned_agent = AutoAgent.from_repo("ix-hub/swe-agent", revision="main")
    print(f"   ✓ Loaded: {versioned_agent.__class__.__name__}")
except Exception as e:
    print(f"   ⚠ Skipped: {e}")
print()

print("=" * 70)
print("✅ Quickstart complete!")
print("=" * 70)
print()
print("Next steps:")
print("  • See README.md for more examples")
print("  • Check docs/REPOSITORY_STANDARDS.md to create your own")
print("  • Explore ix-hub/ for example implementations")

