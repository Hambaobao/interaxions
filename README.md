# Interaxions

Dynamic loading framework for agents and environments, inspired by HuggingFace Transformers.

## Features

- 🚀 **Dynamic Loading** - Load agents/environments from builtin, local, or remote repositories
- 🏷️ **Version Control** - Support Git tags, branches, and commits
- 🔒 **Multi-Process Safe** - File locks for concurrent access
- 💾 **Smart Caching** - Three-level cache for optimal performance
- 🌐 **Flexible Sources** - GitHub, GitLab, or self-hosted Git servers

## Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

```python
from interaxions import AutoAgent, AutoEnvironmentFactory

# Load agent
agent = AutoAgent.from_repo("swe-agent")

# Load environment factory
env_factory = AutoEnvironmentFactory.from_repo("swe-bench")

# Get environment instance
env = env_factory.get_from_oss(
    bucket_name="bucket",
    object_key="data.json",
    oss_region="us-west-2"
)

# Create task
task = agent.create_task(name="solve", env=env)
```

## Loading Sources

### 1. Builtin (fastest)
```python
agent = AutoAgent.from_repo("swe-agent")
```

### 2. Local Repository
```python
agent = AutoAgent.from_repo("./my-agent")
agent = AutoAgent.from_repo("ix-hub/swe-agent", revision="v1.0.0")
```

### 3. Remote Repository
```python
# GitHub (default)
agent = AutoAgent.from_repo("username/repo")

# Custom Git service
import os
os.environ["IX_ENDPOINT"] = "https://gitlab.com"
agent = AutoAgent.from_repo("username/repo")
```

## Environment Variables

```bash
IX_HOME=/custom/path          # Cache directory (default: ~/.interaxions)
IX_ENDPOINT=https://gitlab.com # Git service URL (default: GitHub)
IX_OFFLINE=true               # Disable remote downloads
```

## Creating Your Own

See [Repository Standards](docs/REPOSITORY_STANDARDS.md) for requirements to create compatible agents and environments.

**Minimum requirements:**
- `config.yaml` with `type`, `repo_type`, `image` (for agents)
- `agent.py` or `env.py` with proper base class inheritance
- Implement `create_task()` method returning `hera.workflows.Task`

## Documentation

- [Repository Standards](docs/REPOSITORY_STANDARDS.md) - Complete requirements and guidelines
- [Examples](examples/) - Example implementations

## Project Structure

```
interaxions/
├── agents/          # Official agent implementations
├── environments/    # Official environment implementations
└── hub/            # Dynamic loading system

ix-hub/             # Example third-party implementations
├── swe-agent/
├── swe-agent-lite/
├── code-reviewer-agent/
├── swe-bench/
└── custom-benchmark/
```

## Development

```bash
# Install dependencies
pip install -e .

# Run examples
python examples/quickstart.py
```

## License

MIT
