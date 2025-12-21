# Repository Standards

Requirements for creating third-party agent and environment repositories compatible with Interaxions.

## Quick Reference

### Agent Repository

**Files:**
```
your-agent/
├── config.yaml    # Required
├── agent.py       # Required
└── templates/     # Optional
```

**config.yaml:**
```yaml
type: "your-agent"
repo_type: "agent"
image: "your-image:tag"
```

**agent.py:**
```python
from interaxions.agents.base_agent import BaseAgent, BaseAgentConfig
from hera.workflows import Task, UserContainer

class YourAgentConfig(BaseAgentConfig):
    type: str = "your-agent"
    repo_type: str = "agent"
    image: str = "your-image:tag"

class YourAgent(BaseAgent[YourAgentConfig]):
    def create_task(self, name: str, env, **kwargs) -> Task:
        container = UserContainer(name=name, image=self.config.image, ...)
        return Task(name=name, template=container)
```

### Environment Repository

**Files:**
```
your-env/
├── config.yaml    # Required
├── env.py         # Required
└── templates/     # Optional
```

**config.yaml:**
```yaml
type: "your-env"
repo_type: "environment"
```

**env.py:**
```python
from interaxions.environments.base_environment import (
    BaseEnvironmentFactory, BaseEnvironment, BaseEnvironmentConfig
)
from hera.workflows import Task, UserContainer

class YourEnvConfig(BaseEnvironmentConfig):
    type: str = "your-env"
    repo_type: str = "environment"

class YourEnvironment(BaseEnvironment):
    def create_task(self, name: str, **kwargs) -> Task:
        container = UserContainer(name=name, ...)
        return Task(name=name, template=container)

class YourEnvFactory(BaseEnvironmentFactory[YourEnvConfig]):
    def get_instance(self, **kwargs) -> YourEnvironment:
        return YourEnvironment(...)
```

## Requirements

### Hard Requirements (Must Have)

| Requirement | Agent | Environment |
|------------|-------|-------------|
| `config.yaml` | ✅ | ✅ |
| `type` field | ✅ | ✅ |
| `repo_type` field | ✅ ("agent") | ✅ ("environment") |
| `image` field | ✅ | ❌ |
| Inherit from base class | ✅ BaseAgent | ✅ BaseEnvironment & BaseEnvironmentFactory |
| Implement `create_task()` | ✅ | ✅ |
| Return `hera.workflows.Task` | ✅ | ✅ |

### Optional (Best Practices)

- Type hints
- Docstrings
- `templates/` directory
- README.md
- Git tags for versions

## Usage

```python
from interaxions import AutoAgent, AutoEnvironmentFactory

# Your implementations work automatically
agent = AutoAgent.from_repo("username/your-agent")
env_factory = AutoEnvironmentFactory.from_repo("username/your-env")

# Standard interface
env = env_factory.get_instance(...)
task = agent.create_task(name="task", env=env)
```

## Validation

Validate your repository before publishing:

```python
# Check if repository structure is valid
from pathlib import Path

repo = Path("./your-agent")
assert (repo / "config.yaml").exists()
assert (repo / "agent.py").exists()  # or env.py for environments
```

## Common Patterns

### Custom Config Fields

```python
class MyAgentConfig(BaseAgentConfig):
    type: str = "my-agent"
    repo_type: str = "agent"
    image: str = "my-image:tag"
    # Add custom fields
    max_retries: int = 3
    timeout: int = 300
```

### Template Rendering

```python
class MyAgent(BaseAgent[MyAgentConfig]):
    def create_task(self, name: str, env, **kwargs) -> Task:
        script = self.render_template(
            template_name="main",
            context={"env": env, **kwargs}
        )
        # Use script...
```

### Environment-Specific Logic

```python
def create_task(self, name: str, env, **kwargs) -> Task:
    if env.config.type == "swe-bench":
        # SWE-Bench specific
        pass
    elif env.config.type == "custom":
        # Custom logic
        pass
```

## Examples

See `ix-hub/` directory for complete examples:
- `ix-hub/swe-agent-lite/` - Simple agent
- `ix-hub/custom-benchmark/` - Simple environment

## FAQ

**Q: What if my agent needs different parameters?**
A: Use `**kwargs` in `create_task()` to accept any parameters.

**Q: Can I have multiple factory methods?**
A: Yes, add as many methods as needed (e.g., `get_from_oss`, `get_from_hf`, `get_from_local`).

**Q: Do class names matter?**
A: No, as long as they inherit from the correct base classes.

**Q: How are classes discovered?**
A: By inheritance - Interaxions finds classes that inherit from `BaseAgent` or `BaseEnvironmentFactory`.

## See Also

- [Main README](../README.md) - Quick start guide
- [ix-hub/](../ix-hub/) - Example implementations
