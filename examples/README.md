# Interaxions Examples

This directory contains tutorial examples for the Interaxions framework.

## Quick Start Tutorial

**File:** `quickstart.py`

A comprehensive tutorial that demonstrates the complete workflow:

1. **Define an XJob** - Encapsulate all configurations (model, scaffold, environment, workflow, runtime)
2. **Serialize/Deserialize** - Save and load XJob configurations as JSON
3. **Create Workflow** - Generate Argo Workflows from XJob specifications
4. **Submit or Export** - Deploy to Kubernetes or export as YAML

### Running the Tutorial

```bash
python examples/quickstart.py
```

### What You'll Learn

- **XJob Protocol**: The unified contract for task execution
- **Dynamic Loading**: Load components from built-in, local, or remote repositories
- **Component Configuration**: Configure models, scaffolds, environments, and workflows
- **Workflow Orchestration**: Create and manage Argo Workflows on Kubernetes
- **Serialization**: Store and version XJob configurations

### Key Concepts

#### XJob Structure

```python
XJob(
    # Metadata
    name="...",
    description="...",
    tags={"key": "value"},
    
    # Components
    model=LiteLLMModel(...),    # LLM configuration
    scaffold=Scaffold(...),     # Agent behavior
    environment=Environment(...),  # Task environment
    workflow=Workflow(...),     # Orchestration logic
    runtime=Runtime(...),       # K8s/Argo settings
)
```

#### Dynamic Loading

```python
# Built-in components
AutoScaffold.from_repo("swe-agent")

# Remote repositories
AutoScaffold.from_repo("username/custom-agent")

# Local paths
AutoScaffold.from_repo("./my-agent")

# Specific versions
AutoScaffold.from_repo("user/agent", revision="v1.0.0")
```

#### Workflow Creation

```python
# Load workflow template
workflow_template = AutoWorkflow.from_repo("rollout-and-verify")

# Create workflow from XJob
workflow = workflow_template.create_workflow(job)

# Submit to Argo
workflow.create()

# Or export as YAML
yaml_content = workflow.to_yaml()
```

## Next Steps

- See [Repository Standards](../docs/REPOSITORY_STANDARDS.md) for creating custom components
- See [Main README](../README.md) for framework overview
- See [API Documentation](../docs/README.md) for detailed API reference

