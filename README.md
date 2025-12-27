# Interaxions

A modern, extensible framework for orchestrating AI agents and environments on Kubernetes/Argo Workflows, inspired by HuggingFace Transformers.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- 🎯 **XJob-Based Configuration** - Unified `XJob` schema for complete workflow definition
- 🚀 **Dynamic Loading** - Load components from built-in, local, or remote Git repositories  
- 🔄 **Unified API** - All `Auto*` classes use consistent `from_repo()` interface
- 📦 **Three-Layer Architecture** - Scaffolds, Environments, and Workflows
- 🏷️ **Version Control** - Support for Git tags, branches, and commits
- 🔒 **Multi-Process Safe** - File locks for concurrent access
- 💾 **Smart Caching** - Three-level cache system for optimal performance
- 🌐 **Flexible Sources** - GitHub, GitLab, Gitea, or any Git service via `IX_ENDPOINT`
- ✅ **Comprehensive Testing** - 99 tests with 72% coverage

## 🚀 Quick Start

### Installation

```bash
# Basic installation
pip install interaxions

# With optional dependencies
pip install interaxions[hf]    # HuggingFace datasets
pip install interaxions[oss]   # OSS storage support

# For development
pip install -e ".[dev]"
```

### Basic Usage (XJob-Based API)

```python
from interaxions import AutoWorkflow
from interaxions.schemas import XJob, Scaffold, Environment, Workflow, Runtime, LiteLLMModel

# Define a complete job configuration
job = XJob(
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
        environment_id="astropy__astropy-12907",
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
    environment_id="astropy__astropy-12907",
    source="hf",
    dataset="princeton-nlp/SWE-bench",
    split="test",
)

# Load workflow
workflow_template = AutoWorkflow.from_repo("rollout-and-verify")
```

## 📚 Core Concepts

### 1. XJob - Unified Configuration

`XJob` is the central schema that encapsulates all information needed to run a workflow:

```python
from interaxions.schemas import XJob

job = XJob(
    # Metadata
    name="my-job",
    description="XJob description",
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

All components use the unified `from_repo()` pattern:

```python
# Built-in (by name, no path separators)
component = Auto*.from_repo("component-name")
component = Auto*.from_repo("swe-agent")  # Uses default config

# Local path (contains /, ., or ~)
component = Auto*.from_repo("./my-component")
component = Auto*.from_repo("/absolute/path/to/component")

# Remote repository (Github/Gitlab)
component = Auto*.from_repo("username/repo-name")

# With specific version
component = Auto*.from_repo("username/repo", revision="v1.0.0")
```

**Loading Logic:**
1. If name contains no path separators (`/`, `.`, `~`) → Try as built-in first
2. If built-in not found or path provided → Load from filesystem/remote
3. Built-in modules use default config; external modules require `config.yaml`
4. Remote repositories (format: `username/repo`) use `IX_ENDPOINT` (defaults to GitHub)

## 🎨 Loading Sources

### Built-in Components

Built-in components are Python packages in `interaxions/scaffolds/`, `interaxions/environments/`, etc.

**Two ways to load:**

```python
# Method 1: Direct import (for advanced customization)
from interaxions.scaffolds.swe_agent import SWEAgent, SWEAgentConfig

config = SWEAgentConfig(max_iterations=20)
scaffold = SWEAgent(config=config)

# Method 2: Unified interface (uses default config)
from interaxions import AutoScaffold, AutoWorkflow

scaffold = AutoScaffold.from_repo("swe-agent")  # name only, no paths
workflow = AutoWorkflow.from_repo("rollout-and-verify")
```

**Characteristics:**
- ✅ No `config.yaml` needed (config in Python code)
- ✅ Use simple name: `"swe-agent"`, `"swe-bench"`, `"rollout-and-verify"`
- ✅ Automatically use default configuration
- ❌ Cannot use paths: `"./swe-agent"` will load from filesystem

### External Components

External components are loaded from filesystem paths or remote repositories.

```python
from interaxions import AutoScaffold

# From local directory
scaffold = AutoScaffold.from_repo("./my-custom-scaffold")
scaffold = AutoScaffold.from_repo("/absolute/path/to/scaffold")

# From remote Git repository (GitHub by default)
scaffold = AutoScaffold.from_repo("username/my-scaffold")
scaffold = AutoScaffold.from_repo("username/my-scaffold", revision="v1.0.0")

# From GitLab or other Git services (set IX_ENDPOINT)
# export IX_ENDPOINT=https://gitlab.com
scaffold = AutoScaffold.from_repo("username/my-scaffold")
```

**Characteristics:**
- ✅ Must have `config.yaml` file
- ✅ Must have specific filename: `scaffold.py`, `env.py`, or `workflow.py`
- ✅ Can specify version via `revision` parameter
- ✅ Supports Git tags, branches, commits
- ✅ Uses `IX_ENDPOINT` env var to specify Git service (defaults to GitHub)
- 📦 Cached in `~/.interaxions/hub/`

### Built-in vs External Comparison

| Feature | Built-in | External |
|---------|----------|----------|
| **Loading** | `from_repo("swe-agent")` | `from_repo("./my-scaffold")` or `from_repo("user/repo")` |
| **Location** | `interaxions/scaffolds/` | Filesystem / Remote (GitHub/GitLab/etc.) |
| **Config** | Python code | `config.yaml` required |
| **Versioning** | Package version | Git revision (tags, branches, commits) |
| **Git Service** | N/A | Configurable via `IX_ENDPOINT` (default: GitHub) |
| **Customization** | Direct import + custom config | Via `config.yaml` |
| **Use Case** | Production-ready, battle-tested | Custom experiments, research |

### Environment Loading (Unified API)

```python
from interaxions import AutoEnvironment

# From HuggingFace
env = AutoEnvironment.from_repo(
    repo_name_or_path="swe-bench",
    environment_id="astropy__astropy-12907",
    source="hf",
    dataset="princeton-nlp/SWE-bench",
    split="test",
)

# From OSS (optional dependency)
env = AutoEnvironment.from_repo(
    repo_name_or_path="swe-bench",
    environment_id="astropy__astropy-12907",
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
env1 = factory.get_from_hf("astropy__astropy-12907", "dataset", "test")
env2 = factory.get_from_hf("django__django-11039", "dataset", "test")
env3 = factory.get_from_hf("sympy__sympy-18199", "dataset", "test")
```

## 🔧 Environment Variables (Optional)

All environment variables have sensible defaults and are optional:

| Variable | Description | Default |
|----------|-------------|---------|
| `IX_HOME` | Base directory for Interaxions data | `~/.interaxions` |
| `IX_HUB_CACHE` | Cache directory for hub modules | `~/.interaxions/hub` |
| `IX_OFFLINE` | Enable offline mode (no network) | `false` |
| `IX_ENDPOINT` | Git service endpoint for remote repos | `https://github.com` |

### Using Custom Git Services

By default, remote repositories use GitHub. To use GitLab, Gitea, or enterprise Git:

```bash
# GitLab
export IX_ENDPOINT=https://gitlab.com
scaffold = AutoScaffold.from_repo("username/my-scaffold")
# → Clones from https://gitlab.com/username/my-scaffold.git

# Enterprise GitLab
export IX_ENDPOINT=https://git.company.com
scaffold = AutoScaffold.from_repo("team/project")
# → Clones from https://git.company.com/team/project.git

# Gitea
export IX_ENDPOINT=https://gitea.io
```

**Note**: The system automatically appends `.git` to repository paths.

### Accessing Private Repositories

All `Auto*.from_repo()` methods support authentication for private repositories using `username` and `token` parameters:

```python
from interaxions import AutoScaffold

# Load from private repository
scaffold = AutoScaffold.from_repo(
    repo_name_or_path="company/private-agent",
    username="your-username",
    token="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # GitHub PAT
)

# With custom Git service (GitLab)
import os
os.environ["IX_ENDPOINT"] = "https://gitlab.company.com"

scaffold = AutoScaffold.from_repo(
    repo_name_or_path="team/private-agent",
    username="gitlab-user",
    token="glpat-xxxxxxxxxxxxxxxxxxxx"  # GitLab token
)

# Best practice: Use environment variables
git_username = os.getenv("GIT_USERNAME")
git_token = os.getenv("GIT_TOKEN")

scaffold = AutoScaffold.from_repo(
    repo_name_or_path="company/private-agent",
    username=git_username,
    token=git_token
)
```

**Supported**: `AutoScaffold`, `AutoEnvironmentFactory`, `AutoEnvironment`, `AutoWorkflow`

**Authentication format**: The system constructs URLs like `https://username:token@host/repo.git`, similar to:
```bash
git clone https://username:token@gitlab.company.com/test-user/Demo-Agent.git
```

**Token generation**:
- GitHub: https://github.com/settings/tokens (scope: `repo`)
- GitLab: Settings > Access Tokens (scope: `read_repository`)

## 📦 Creating Custom Components

Custom components are external modules loaded via filesystem paths or remote repositories.

See [Repository Standards](docs/REPOSITORY_STANDARDS.md) for detailed requirements.

### Minimum Requirements

**Scaffold Repository:**
```
my-scaffold/
├── config.yaml           # Required: type: my-scaffold, templates: {...}
├── scaffold.py           # Required: Class inheriting from BaseScaffold
└── templates/            # Optional: Jinja2 templates
    └── main.j2
```

Example `config.yaml`:
```yaml
type: my-scaffold
image: my-scaffold:latest
templates:
  main: templates/main.j2
  sidecar: templates/sidecar.j2
```

**Environment Repository:**
```
my-environment/
├── config.yaml           # Required: type: my-environment, templates: {...}
├── env.py                # Required: Factory inheriting from BaseEnvironmentFactory
└── templates/            # Optional: Jinja2 templates
    └── verify.j2
```

Example `config.yaml`:
```yaml
type: my-environment
templates:
  evaluation: templates/evaluation.j2
  setup: templates/setup.j2
```

**Workflow Repository:**
```
my-workflow/
├── config.yaml           # Required: type: my-workflow, templates: {...}
├── workflow.py           # Required: Class inheriting from BaseWorkflow
└── templates/            # Optional: Jinja2 templates
    └── main.j2
```

Example `config.yaml`:
```yaml
type: my-workflow
templates:
  main: templates/main.j2
  verify: templates/verify.j2
```

**Key Points:**
- ✅ `config.yaml` is **required** for external components
- ✅ Use specific filenames: `scaffold.py`, `env.py`, `workflow.py`
- ✅ Classes must inherit from base classes: `BaseScaffold`, `BaseEnvironmentFactory`, `BaseWorkflow`
- ✅ Implement required methods: `create_task()` for scaffolds/environments, `create_workflow()` for workflows
- ✅ `templates/` directory is optional but recommended for all component types
- ✅ Templates in `config.yaml` are loaded as strings (e.g., `templates/main.j2`)
- ✅ Built-in components don't need `config.yaml` (config in Python code)

## 🧪 Testing

```bash
# Run all tests (99 passed, 4 skipped)
pytest

# Run specific test categories
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
pytest -m e2e           # End-to-end tests

# With coverage (currently 72%)
pytest --cov=interaxions --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Test Statistics:**
- ✅ 99 tests passing
- ⏭️ 4 tests skipped (3 OSS optional dependency, 1 needs mock environment)
- 📊 72% code coverage
- ⚡ ~4s total runtime

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
├── schemas/            # Pydantic schemas (XJob, Scaffold, etc.)
│   ├── job.py
│   └── models.py
└── hub/                # Dynamic loading system
    ├── auto.py         # Auto* classes
    ├── hub_manager.py  # Repository management
    └── constants.py    # Configuration

tests/                  # Comprehensive test suite (99 passed, 72% coverage)
├── unit/               # Unit tests (schemas, models)
├── integration/        # Integration tests (auto loading, factories)
├── e2e/                # End-to-end tests (full pipeline)
├── fixtures/           # Test data and mock repositories
│   ├── mock_repos/     # Mock scaffold/workflow repos for testing
│   └── sample_data.py  # Sample data generators
└── conftest.py         # Shared fixtures and test configuration

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

# Run tests (should see 99 passed, 4 skipped)
pytest

# Run specific test categories
pytest -m unit          # Fast unit tests
pytest -m integration   # Integration tests
pytest -m e2e           # End-to-end tests

# Check coverage
pytest --cov=interaxions --cov-report=term

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
