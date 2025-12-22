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
from hera.workflows import Task, Container
from typing import Any

class YourAgentConfig(BaseAgentConfig):
    type: str = "your-agent"
    repo_type: str = "agent"
    image: str = "your-image:tag"

class YourAgent(BaseAgent):
    config_class = YourAgentConfig
    config: YourAgentConfig
    
    def create_task(
        self,
        *,
        context: dict,
        name: Optional[str] = None,
        **kwargs: Any
    ) -> Task:
        if name is None:
            name = f"agent-{context.get('id', 'default')}"
        container = Container(
            name=name,
            image=self.config.image,
            command=["python", "main.py"],
        )
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
from hera.workflows import Task, Container
from typing import Any

class YourEnvConfig(BaseEnvironmentConfig):
    type: str = "your-env"
    repo_type: str = "environment"

class YourEnvironment(BaseEnvironment):
    environment_id: str
    
    def create_task(
        self,
        *,
        data_path: str,
        name: Optional[str] = None,
        **kwargs: Any
    ) -> Task:
        if name is None:
            name = f"env-{self.environment_id}"
        container = Container(
            name=name,
            image="your-env:latest",
            command=["python", "evaluate.py", data_path],
        )
        return Task(name=name, template=container)

class YourEnvFactory(BaseEnvironmentFactory):
    config_class = YourEnvConfig
    config: YourEnvConfig
    
    def get_instance(self, environment_id: str, **kwargs) -> YourEnvironment:
        return YourEnvironment(environment_id=environment_id)
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

### `create_task()` Interface

All agents and environments **must** implement:

```python
def create_task(self, **kwargs: Any) -> Task:
    ...
```

**Design Philosophy:**

The base class uses `**kwargs` for maximum flexibility, but **concrete implementations should explicitly declare their parameters** for better IDE support and type checking.

**Common Conventions:**

- `name` (Optional[str]): Task name. Auto-generated if not provided (recommended).
- `inputs` (Optional[List[ArgoArtifact]]): Input artifacts.
- `outputs` (Optional[List[ArgoArtifact]]): Output artifacts.

**Implementation Pattern:**

Each implementation should:
1. Explicitly declare required parameters
2. Make `name` optional with auto-generation
3. Use `*` to enforce keyword-only arguments
4. Keep `**kwargs` for extensibility

```python
def create_task(
    self,
    *,  # Force keyword arguments
    context: MyContext,  # Your required parameter
    name: Optional[str] = None,  # Auto-generated if not provided
    inputs: Optional[List[ArgoArtifact]] = None,
    outputs: Optional[List[ArgoArtifact]] = None,
    custom_param: str = "default",
    **kwargs: Any,  # Additional extensibility
) -> Task:
    """
    Create a task for MyAgent.
    
    Args:
        context: Agent execution context (required).
        name: Task name. Auto-generated from context if not provided.
        inputs: Input artifacts.
        outputs: Output artifacts.
        custom_param: Your custom parameter.
        **kwargs: Additional options.
    
    Returns:
        Hera Task object.
    """
    # Auto-generate name if not provided
    if name is None:
        name = f"agent-{context.instance_id}"
    
    # ... implementation
    return Task(name=name, template=container)
```

**Benefits of This Pattern:**

- ✅ **IDE Support**: Autocomplete shows all parameters
- ✅ **Type Safety**: Static type checking works
- ✅ **Auto-naming**: Tasks get semantic names automatically
- ✅ **Flexibility**: Callers can override name when needed
- ✅ **Workflow-friendly**: Workflows don't need to manage task names
    
    Required keyword arguments:
        context: MyContext instance with agent parameters
    
    Optional keyword arguments:
        inputs: Input artifacts
        outputs: Output artifacts
        custom_param: Your custom parameter
    """
    ...
```

**Important:**
- Document all parameters in the method's docstring
- Different implementations can have completely different parameters
- Users select implementations via version control (`from_repo(..., revision="v1.0")`)

### Optional (Best Practices)

- Type hints
- Docstrings
- `templates/` directory
- README.md
- Git tags for versions

## Usage

```python
from interaxions import AutoScaffold, AutoEnvironmentFactory

# Your implementations work automatically
agent = AutoScaffold.from_repo("username/your-agent")
env_factory = AutoEnvironmentFactory.from_repo("username/your-env")

# Standard interface
env = env_factory.get_instance(...)
task = agent.create_task(context=context)  # name auto-generated
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
class MyAgent(BaseAgent):
    config_class = MyAgentConfig
    config: MyAgentConfig
    
    def create_task(
        self,
        *,
        env,
        name: Optional[str] = None,
        **kwargs: Any
    ) -> Task:
        if name is None:
            name = f"agent-{env.environment_id}"
        script = self.render_template(
            template_name="main",
            context={"env_id": env.environment_id, **kwargs}
        )
        container = Container(
            name=name,
            image=self.config.image,
            command=["bash", "-c", script]
        )
        return Task(name=name, template=container)
```

### Environment-Specific Logic

```python
def create_task(
    self,
    *,
    env,
    name: Optional[str] = None,
    **kwargs: Any
) -> Task:
    if name is None:
        name = f"agent-{env.environment_id}"
    if env.config.type == "swe-bench":
        # SWE-Bench specific
        image = "swe-bench:latest"
    elif env.config.type == "custom":
        # Custom logic
        image = "custom:latest"
    
    container = Container(name=name, image=image, ...)
    return Task(name=name, template=container)
```

## Examples

See `ix-hub/` directory for complete examples:
- `ix-hub/swe-agent-lite/` - Simple agent
- `ix-hub/custom-benchmark/` - Simple environment

## FAQ

**Q: What parameters should `create_task()` accept?**  
A: No required parameters in the signature. Use `**kwargs` in base class, but concrete implementations should explicitly declare their parameters. The `name` parameter should be optional and auto-generated if not provided. Document all parameters in your docstring.

**Q: Must I support `inputs` and `outputs` parameters?**  
A: No, but it's recommended if your task needs artifacts. Many workflows use them to connect tasks together.

**Q: How do I make `name` auto-generated?**  
A: Make it optional with default `None`, then generate it in the method:
```python
def create_task(
    self,
    *,
    context: MyContext,
    name: Optional[str] = None,
    **kwargs: Any
) -> Task:
    if name is None:
        name = f"agent-{context.instance_id}"
    ...
```

**Q: How do I make my parameters required?**  
A: Define them after the `*` separator without default values:
```python
def create_task(
    self,
    *,
    my_required_param: str,  # No default = required
    name: Optional[str] = None,  # Has default = optional
    **kwargs: Any
) -> Task:
    ...
```
A: No, but it's recommended if your task needs artifacts. Many workflows use them to connect tasks together.

**Q: Can different versions have different `create_task` signatures?**
A: Yes! That's the power of version control. Users select the version they need via `from_repo(..., revision="v2.0")`.

**Q: What if my agent needs different parameters?**
A: Define them after the `*` separator to make them keyword-only:
```python
def create_task(self, name: str, *, my_param: str, **kwargs: Any) -> Task:
    ...
```

**Q: Can I have multiple factory methods?**
A: Yes, add as many methods as needed (e.g., `get_from_oss`, `get_from_hf`, `get_from_local`).

**Q: Do class names matter?**
A: No, as long as they inherit from the correct base classes.

**Q: How are classes discovered?**
A: By inheritance - Interaxions finds classes that inherit from `BaseAgent` or `BaseEnvironmentFactory`.

## See Also

- [Main README](../README.md) - Quick start guide
- [ix-hub/](../ix-hub/) - Example implementations
