# Interaxions

A modern, extensible framework for orchestrating AI agents and environments on Kubernetes/Argo Workflows, inspired by HuggingFace Transformers.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- 🎯 **Job-Based Configuration** - Unified `Job` schema for complete workflow definition
- 🚀 **Dynamic Loading** - Load components from built-in, local, or remote Git repositories  
- 🔄 **Unified API** - All `Auto*` classes use consistent `from_repo()` interface
- 📦 **Three-Layer Architecture** - Scaffolds, Environments, and Workflows
- 🏷️ **Version Control** - Support for Git tags, branches, and commits
- 🔒 **Multi-Process Safe** - File locks for concurrent access
- 💾 **Smart Caching** - Three-level cache system for optimal performance
- 🌐 **Flexible Sources** - GitHub, GitLab, HuggingFace, OSS, or custom sources
- ✅ **Comprehensive Testing** - 53 unit tests with pytest

## 🚀 Quick Start

### Installation

```bash
# Basic installation
pip install interaxions

# With optional dependencies
pip install interaxions[argo]  # Argo Workflows support
pip install interaxions[hf]    # HuggingFace datasets
pip install interaxions[oss]   # OSS storage support

# For development
pip install -e ".[dev]"
```

### Basic Usage (Job-Based API)

```python
from interaxions import AutoWorkflow
from interaxions.schemas import Job, Scaffold, Environment, Workflow, Runtime, LiteLLMModel

# Define a complete job configuration
job = Job(
    name="fix-django-bug",
    description="Fix Django bug using SWE-agent",
    tags=["swe-bench", "django"],
    labels={"priority": "high", "team": "research"},
    
    # Model configuration
    model=LiteLLMModel(
        type="litellm",
        provider="openai",
        model="gpt-4",
        base_url="https://api.openai.com/v1",
        api_key="your-api-key",
    ),
    
    # Scaffold (agent) configuration
    scaffold=Scaffold(
        repo_name_or_path="swe-agent",
        params={"max_iterations": 10},
    ),
    
    # Environment configuration
    environment=Environment(
        repo_name_or_path="swe-bench",
        environment_id="django__django-12345",
        source="hf",
        params={
            "dataset": "princeton-nlp/SWE-bench",
            "split": "test",
        },
    ),
    
    # Workflow configuration
    workflow=Workflow(
        repo_name_or_path="rollout-and-verify",
        params={},
    ),
    
    # Runtime configuration
    runtime=Runtime(
        namespace="experiments",
        service_account="argo-workflow",
        ttl_seconds_after_finished=3600,
    ),
)

# Create and submit workflow
workflow_template = AutoWorkflow.from_repo(job.workflow.repo_name_or_path)
workflow = workflow_template.create_workflow(job)
workflow.create()  # Submit to Argo
```

### Quick API (One-Step Loading)

```python
from interaxions import AutoScaffold, AutoEnvironment, AutoWorkflow

# Load scaffold
scaffold = AutoScaffold.from_repo("swe-agent")

# Load environment (unified API)
env = AutoEnvironment.from_repo(
    repo_name_or_path="swe-bench",
    environment_id="django__django-12345",
    source="hf",
    dataset="princeton-nlp/SWE-bench",
    split="test",
)

# Load workflow
workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
```

## 📚 Core Concepts

### 1. Job - Unified Configuration

`Job` is the central schema that encapsulates all information needed to run a workflow:

```python
from interaxions.schemas import Job

job = Job(
    # Metadata
    name="my-job",
    description="Job description",
    tags=["tag1", "tag2"],
    labels={"key": "value"},
    
    # Components (all use from_repo pattern)
    model=...,        # LLM configuration
    scaffold=...,     # Agent/scaffold configuration
    environment=...,  # Environment/data configuration  
    workflow=...,     # Workflow orchestration
    runtime=...,      # Kubernetes/Argo settings
)
```

### 2. Three-Layer Architecture

**Scaffolds** (formerly Agents)
- High-level orchestration logic
- Can manage single or multiple agents internally
- Example: `swe-agent`

**Environments**
- Test environments and evaluation datasets
- Support HuggingFace, OSS, and custom sources
- Example: `swe-bench`

**Workflows**
- Define execution order and dependencies
- Generate Argo Workflows
- Example: `rollout-and-verify`

### 3. Dynamic Loading

All components use the `from_repo()` pattern:

```python
# Built-in
component = Auto*.from_repo("component-name")

# Local path
component = Auto*.from_repo("./my-component")

# Remote repository (GitHub)
component = Auto*.from_repo("username/repo-name")

# With specific version
component = Auto*.from_repo("username/repo", revision="v1.0.0")
```

## 🎨 Loading Sources

### Built-in Components
```python
from interaxions import AutoScaffold, AutoEnvironment, AutoWorkflow

# Load built-in components
scaffold = AutoScaffold.from_repo("swe-agent")
workflow = AutoWorkflow.from_repo("rollout-and-verify")
```

### Environment Loading (Unified API)

```python
from interaxions import AutoEnvironment

# From HuggingFace
env = AutoEnvironment.from_repo(
    repo_name_or_path="swe-bench",
    environment_id="django-123",
    source="hf",
    dataset="princeton-nlp/SWE-bench",
    split="test",
)

# From OSS
env = AutoEnvironment.from_repo(
    repo_name_or_path="swe-bench",
    environment_id="django-123",
    source="oss",
    dataset="swe-bench-data",
    split="test",
    oss_region="cn-hangzhou",
    oss_endpoint="oss-cn-hangzhou.aliyuncs.com",
    oss_access_key_id="your-key-id",
    oss_access_key_secret="your-secret",
)
```

### Batch Loading (Factory Pattern)

```python
from interaxions import AutoEnvironmentFactory

# Load factory once
factory = AutoEnvironmentFactory.from_repo("swe-bench")

# Create multiple environments efficiently
env1 = factory.get_from_hf("django-123", "dataset", "test")
env2 = factory.get_from_hf("flask-456", "dataset", "test")
env3 = factory.get_from_hf("numpy-789", "dataset", "test")
```

## 🔧 Environment Variables (Optional)

All environment variables have sensible defaults and are optional:

| Variable | Description | Default |
|----------|-------------|---------|
| `IX_HOME` | Base directory for Interaxions data | `~/.interaxions` |
| `IX_HUB_CACHE` | Cache directory for hub modules | `~/.interaxions/hub` |
| `IX_OFFLINE` | Enable offline mode (no network) | `false` |
| `IX_ENDPOINT` | Custom Git endpoint for remote repos | GitHub |

Example:
```bash
export IX_HOME=/custom/path
export IX_OFFLINE=true
```

## 📦 Creating Custom Components

See [Repository Standards](docs/REPOSITORY_STANDARDS.md) for detailed requirements.

### Minimum Requirements

**Scaffold Repository:**
```
my-scaffold/
├── config.yaml           # type: my-scaffold
├── agent.py              # Class inheriting from BaseScaffold
└── templates/            # Optional Jinja2 templates
    └── main.j2
```

**Environment Repository:**
```
my-environment/
├── config.yaml           # type: my-environment
└── env.py                # Factory inheriting from BaseEnvironmentFactory
```

**Workflow Repository:**
```
my-workflow/
├── config.yaml           # type: my-workflow
└── workflow.py           # Class inheriting from BaseWorkflow
```

All components must implement:
- `from_repo(repo_name_or_path, revision)` class method
- `create_task(job, **kwargs)` or `create_workflow(job, **kwargs)` method

## 🧪 Testing

```bash
# Run unit tests (fast, reliable)
pytest -m unit

# Run all tests
pytest

# With coverage
pytest --cov=interaxions --cov-report=html

# View coverage report
open htmlcov/index.html
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

## 📁 Project Structure

```
interaxions/
├── scaffolds/          # Agent scaffold implementations
│   ├── base_scaffold.py
│   └── swe_agent/
├── environments/       # Environment implementations
│   ├── base_environment.py
│   └── swe_bench/
├── workflows/          # Workflow implementations
│   ├── base_workflow.py
│   └── rollout_and_verify/
├── schemas/            # Pydantic schemas (Job, Scaffold, etc.)
│   ├── job.py
│   └── models.py
└── hub/                # Dynamic loading system
    ├── auto.py         # Auto* classes
    ├── hub_manager.py  # Repository management
    └── constants.py    # Configuration

tests/                  # Comprehensive test suite
├── unit/               # Unit tests (53 tests, all passing)
├── integration/        # Integration tests
├── e2e/                # End-to-end tests
└── conftest.py         # Shared fixtures

examples/               # Usage examples
└── quickstart.py       # Complete tutorial
```

## 🔄 Development Workflow

```bash
# Clone repository
git clone https://github.com/Hambaobao/interaxions.git
cd interaxions

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -m unit

# Run examples
python examples/quickstart.py

# Build package
python -m build

# Check package
twine check dist/*
```

## 📖 Documentation

- **[Repository Standards](docs/REPOSITORY_STANDARDS.md)** - Complete guide for creating custom components
- **[Testing Guide](tests/README.md)** - Comprehensive testing documentation
- **[Examples](examples/)** - Example implementations and tutorials

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest -m unit`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- Inspired by [HuggingFace Transformers](https://github.com/huggingface/transformers)
- Built on [Hera](https://github.com/argoproj-labs/hera) for Argo Workflows
- Powered by [Pydantic](https://github.com/pydantic/pydantic) for data validation

## 🔗 Links

- **Homepage**: https://github.com/Hambaobao/interaxions
- **Issues**: https://github.com/Hambaobao/interaxions/issues
- **PyPI**: Coming soon

---

Made with ❤️ for the AI agent research community
