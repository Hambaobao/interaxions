# Interaxions

A lightweight, extensible framework for orchestrating AI agents and evaluation environments on Kubernetes/Argo Workflows, inspired by HuggingFace Transformers.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- 🎯 **XJob-Based Configuration** — Minimal, framework-neutral `XJob` schema
- 🚀 **Dynamic Loading** — Load components from local paths or remote Git repositories via `Auto*` classes
- 🔄 **Unified Entry File** — Every repository exposes a single `ix.py` entry point
- 📦 **Three-Layer Architecture** — Scaffolds, Environments, and Workflows as peers
- 🏷️ **Version Control** — Git tags, branches, and commit hashes
- 🔒 **Multi-Process Safe** — File locking for concurrent cache access
- 💾 **Smart Caching** — Three-level cache for optimal performance
- 🌐 **Flexible Git Sources** — GitHub, GitLab, Gitea, or any Git service via `IX_ENDPOINT`

---

## 🚀 Quick Start

### Installation

```bash
# Core
pip install interaxions

# For development
pip install -e ".[dev]"
```

### Defining a Job

`XJob` is the single source of truth for a unit of work. All component
configurations (scaffold, environment, model, …) live inside
`workflow.params` — the workflow itself defines and validates what it needs.

```python
from interaxions import AutoWorkflow
from interaxions.schemas import XJob, WorkflowConfig, RuntimeConfig

job = XJob(
    name="fix-django-bug",
    description="Run SWE-agent on a SWE-bench instance",
    tags=["swe-bench", "django"],
    labels={"priority": "high", "team": "research"},

    workflow=WorkflowConfig(
        repo_name_or_path="Agent-Hub/SWE-rollout-verify-postprocess-workflow",
        revision="v1.0.0",
        params={
            # Each workflow defines its own params schema
            "scaffold": {
                "repo_name_or_path": "Agent-Hub/SWE-agent",
                "revision": "v1.0.0",
                "params": {"max_iterations": 50},
            },
            "environment": {
                "repo_name_or_path": "Agent-Hub/SWE-bench",
                "revision": "v1.0.0",
                "id": "django__django-12345",
                "params": {"fix_hack": True},
            },
            "model": {
                "type": "litellm",
                "provider": "openai",
                "model": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-...",
            },
        },
    ),

    runtime=RuntimeConfig(
        namespace="experiments",
        service_account="argo-workflow",
        ttl_seconds_after_finished=3600,
        extra_params={
            "labels": {"env": "prod"},
            "node_selector": {"gpu": "true"},
        },
    ),
)

# Submit to Argo
workflow_template = AutoWorkflow.from_repo(
    job.workflow.repo_name_or_path,
    revision=job.workflow.revision,
)
argo_workflow = workflow_template.create_workflow(job)
argo_workflow.create()
```

---

## 📚 Core Concepts

### XJob — Framework-Neutral Configuration

`XJob` carries only what is universally required:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | `str` (auto) | Unique identifier (UUID, auto-generated) |
| `name` | `str` | Human-readable name |
| `tags` / `labels` | `list` / `dict` | Metadata for search and filtering |
| `workflow` | `WorkflowConfig` | Which workflow repo to load + all workflow-specific params |
| `runtime` | `RuntimeConfig` | Kubernetes / Argo Workflows settings |
| `extra_params` | `dict` | Arbitrary job-level extras (optional) |

**Design principle:** `XJob` makes no assumptions about what a workflow needs.
All component configs go into `workflow.params`; the workflow validates them
with its own Pydantic model.

### Three-Layer Architecture

```
XJob
 └── workflow.params
       ├── scaffold   → AutoScaffold  → BaseScaffold.create_task()
       ├── environment→ AutoEnvironment→ BaseEnvironment.get() + create_task()
       └── model      → workflow-defined
```

**Scaffold** (`BaseScaffold`)
- Wraps an AI agent (e.g. SWE-agent)
- Implements `create_task(job, environment) → hera.Task`

**Environment** (`BaseEnvironment`)
- Wraps a benchmark / evaluation dataset
- Implements `get(id) → Environment` (pure data) and `create_task(job, environment) → hera.Task`
- Credentials (OSS keys, API tokens) are read from **environment variables**, never passed as parameters

**Workflow** (`BaseWorkflow`)
- Orchestrates scaffolds and environments into a full Argo Workflow DAG
- Implements `create_workflow(job) → hera.Workflow`
- Defines and validates its own `workflow.params` schema

### Auto Classes — Dynamic Loading

All three Auto classes share the same interface:

```python
from interaxions import AutoScaffold, AutoEnvironment, AutoWorkflow

# From a remote Git repository (uses IX_ENDPOINT, default: GitHub)
scaffold  = AutoScaffold.from_repo("username/swe-agent", revision="v1.0.0")
env_task  = AutoEnvironment.from_repo("username/swe-bench", revision="v2.0.0")
workflow  = AutoWorkflow.from_repo("username/swe-rollout-verify")

# From a local path (for development / testing)
scaffold  = AutoScaffold.from_repo("./my-agent")
env_task  = AutoEnvironment.from_repo("/abs/path/to/my-bench")
workflow  = AutoWorkflow.from_repo("./my-workflow")

# Private repositories
scaffold  = AutoScaffold.from_repo(
    "company/private-agent",
    username="your-username",
    token="ghp_xxxx",          # or read from env var
)
```

**Loading rules:**
- **Absolute paths** (e.g. `/abs/path/to/repo`) → loaded directly from the filesystem
- **Relative paths** (e.g. `./my-agent`) → resolved relative to the current working directory
- **Remote repos** (e.g. `org/repo`) → cloned from `IX_ENDPOINT` (default: GitHub) when not found locally
- Results are cached; pinned revisions (`revision="v1.0.0"`) are cache-hit on repeat calls

### Repository Structure

Every `ix-hub` repository must contain:

```
my-component/
├── config.yaml      # Required — repo metadata
└── ix.py            # Required — exactly one class inheriting from the base class
```

**`config.yaml` minimum:**
```yaml
type: my-component    # required for environment / workflow; user-defined for scaffold
# repo_type is optional — defaults to the base class type (scaffold | environment | workflow)
```

**`ix.py` pattern (scaffold example):**
```python
from interaxions.scaffolds.base_scaffold import BaseScaffold, BaseScaffoldConfig

class MyScaffoldConfig(BaseScaffoldConfig):
    type: str = "my-scaffold"
    image: str = "my-agent:latest"

class MyScaffold(BaseScaffold):
    config_class = MyScaffoldConfig
    config: MyScaffoldConfig

    def create_task(self, job, environment, **kwargs):
        ...
```

**`ix.py` pattern (environment example):**
```python
import os
from interaxions.environments.base_environment import BaseEnvironment, BaseEnvironmentConfig
from interaxions.schemas.task import Environment

class MyBenchConfig(BaseEnvironmentConfig):
    type: str = "my-bench"

class MyBench(BaseEnvironment):
    config_class = MyBenchConfig

    def get(self, id: str, **kwargs) -> Environment:
        # Read credentials from environment variables
        oss_key = os.environ["OSS_ACCESS_KEY_ID"]
        data = load_from_oss(id, oss_key)
        return Environment(id=id, type=self.config.type, data=data)

    def create_task(self, job, environment, **kwargs):
        ...
```

**`ix.py` pattern (workflow example):**
```python
from pydantic import BaseModel
from interaxions.hub import AutoScaffold, AutoEnvironment
from interaxions.schemas import ScaffoldConfig, EnvironmentConfig
from interaxions.schemas.task import Environment
from interaxions.workflows.base_workflow import BaseWorkflow, BaseWorkflowConfig

class MyWorkflowParams(BaseModel):
    scaffold: ScaffoldConfig
    environment: EnvironmentConfig

class MyWorkflowConfig(BaseWorkflowConfig):
    type: str = "my-workflow"

class MyWorkflow(BaseWorkflow):
    config_class = MyWorkflowConfig

    def create_workflow(self, job, **kwargs):
        params = MyWorkflowParams(**job.workflow.params)

        scaffold  = AutoScaffold.from_repo(params.scaffold.repo_name_or_path)
        env_task  = AutoEnvironment.from_repo(params.environment.repo_name_or_path)
        env: Environment = env_task.get(params.environment.id)

        scaffold_task = scaffold.create_task(job, env)
        verify_task   = env_task.create_task(job, env)

        with hera.Workflow(name=..., namespace=job.runtime.namespace) as wf:
            scaffold_task >> verify_task

        return wf
```

---

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `IX_HOME` | Base directory for Interaxions data | `~/.interaxions` |
| `IX_HUB_CACHE` | Cache directory for hub modules | `~/.interaxions/hub` |
| `IX_OFFLINE` | Disable all network access | `false` |
| `IX_ENDPOINT` | Git service base URL for remote repos | `https://github.com` |

**Component credentials** (OSS keys, HF tokens, API keys) are **not** stored
in `XJob`. Environment repo maintainers read them from their own environment
variables at runtime.

---

## 📦 Schema Reference

### `WorkflowConfig`

```python
WorkflowConfig(
    repo_name_or_path="org/repo",   # required
    revision="v1.0.0",              # optional Git ref
    username=None,                  # optional auth
    token=None,                     # optional auth
    params={},                      # workflow-defined; shape is up to the workflow
)
```

### `RuntimeConfig`

```python
RuntimeConfig(
    namespace="experiments",        # required Kubernetes namespace
    service_account=None,           # optional
    image_pull_policy="IfNotPresent",
    active_deadline_seconds=None,
    ttl_seconds_after_finished=None,
    extra_params={
        "labels": {...},
        "annotations": {...},
        "node_selector": {...},
        "tolerations": [...],
        "priority_class_name": "...",
    },
)
```

### `ScaffoldConfig` / `EnvironmentConfig`

Standard vocabulary types you can use inside `workflow.params`:

```python
from interaxions.schemas import ScaffoldConfig, EnvironmentConfig

scaffold_cfg = ScaffoldConfig(
    repo_name_or_path="org/swe-agent",
    revision="v1.0.0",
    params={"max_iterations": 50},
)

env_cfg = EnvironmentConfig(
    repo_name_or_path="org/swe-bench",
    id="django__django-12345",       # required instance id
    params={"fix_hack": True},
)
```

### `Environment` (data carrier)

Returned by `BaseEnvironment.get(id)`:

```python
from interaxions.schemas.task import Environment

env = env_task.get("django__django-12345")
env.id       # "django__django-12345"
env.type     # "swe-bench"
env.data     # {"problem_statement": "...", "repo": "...", ...}
```

Workflows can define typed subclasses for safe field access:

```python
class SWEEnvironment(Environment):
    fix_hack: bool = False

    @classmethod
    def from_environment(cls, env: Environment, env_config: EnvironmentConfig) -> "SWEEnvironment":
        return cls(
            id=env.id, type=env.type, data=env.data,
            fix_hack=env_config.params.get("fix_hack", False),
        )
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# By category
pytest -m unit          # Fast isolated unit tests
pytest -m integration   # Component loading tests (local repos)
pytest -m e2e           # End-to-end pipeline tests

# With coverage
pytest --cov=interaxions --cov-report=html
open htmlcov/index.html
```

The test suite uses local mock repositories in `tests/fixtures/mock_repos/`
(no network access required):

| Mock Repo | Entry Class | Purpose |
|-----------|-------------|---------|
| `test-scaffold/` | `TestScaffold` | Test `AutoScaffold` loading |
| `test-environment/` | `TestEnvironment` | Test `AutoEnvironment` loading + `get()` |
| `test-workflow/` | `TestWorkflow` | Test `AutoWorkflow` loading + template loading |

---

## 📁 Project Structure

```
interaxions/
├── scaffolds/
│   ├── base_scaffold.py        # BaseScaffold + BaseScaffoldConfig
│   └── __init__.py
├── environments/
│   ├── base_environment.py     # BaseEnvironment + BaseEnvironmentConfig
│   └── __init__.py
├── workflows/
│   ├── base_workflow.py        # BaseWorkflow + BaseWorkflowConfig
│   └── __init__.py
├── schemas/
│   ├── job.py                  # XJob
│   ├── workflow.py             # WorkflowConfig
│   ├── runtime.py              # RuntimeConfig
│   ├── scaffold.py             # ScaffoldConfig
│   ├── environment.py          # EnvironmentConfig
│   ├── task.py                 # Environment (data carrier)
│   └── models.py               # OpenAIModel, AnthropicModel, LiteLLMModel
└── hub/
    ├── auto.py                 # AutoScaffold, AutoEnvironment, AutoWorkflow
    ├── hub_manager.py          # Git clone / checkout / caching
    └── constants.py

tests/
├── unit/                       # Schema and model unit tests
├── integration/                # Auto* loading tests (local mock repos)
├── e2e/                        # Full pipeline tests
├── fixtures/
│   └── mock_repos/
│       ├── test-scaffold/      # ix.py + config.yaml
│       ├── test-environment/   # ix.py + config.yaml
│       └── test-workflow/      # ix.py + config.yaml + templates/
└── conftest.py
```

---

## 🔄 Development

```bash
# Setup
git clone https://github.com/Hambaobao/interaxions.git
cd interaxions
pip install -e ".[dev]"

# Test
pytest -m unit          # fastest
pytest                  # all tests

# Coverage
pytest --cov=interaxions --cov-report=term-missing
```

---

## 📖 Documentation

- **[Repository Standards](docs/REPOSITORY_STANDARDS.md)** — How to create custom `ix-hub` repos
- **[XJob User Guide](docs/XJob_User_Guide.md)** — Detailed XJob usage patterns

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Inspired by [HuggingFace Transformers](https://github.com/huggingface/transformers)
- Built on [Hera](https://github.com/argoproj-labs/hera) for Argo Workflows
- Powered by [Pydantic](https://github.com/pydantic/pydantic) for data validation

---

Made with ❤️ for the AI agent research community
