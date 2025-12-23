# Interaxions Test Suite

This directory contains the complete test suite for the Interaxions framework.

## Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_schemas.py      # Schema validation tests
│   ├── test_models.py       # Model (LiteLLMModel) tests
│   └── test_config.py       # Configuration loading tests
│
├── integration/             # Integration tests (component interaction)
│   ├── test_auto_scaffold.py       # AutoScaffold loading tests
│   ├── test_auto_environment.py    # AutoEnvironment loading tests
│   └── test_auto_workflow.py       # AutoWorkflow loading tests
│
├── e2e/                     # End-to-end tests (full pipeline)
│   └── test_full_pipeline.py       # Job → Workflow tests
│
├── fixtures/                # Test fixtures and data
│   ├── sample_data.py       # Sample test data
│   └── mock_repos/          # Mock repositories for testing
│       └── test-scaffold/   # Example mock scaffold
│
└── conftest.py              # Pytest configuration and fixtures
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# End-to-end tests only
pytest -m e2e

# Exclude slow tests
pytest -m "not slow"
```

### Run with coverage
```bash
# Generate coverage report
pytest --cov=interaxions --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

### Run in parallel
```bash
# Run tests in parallel (faster)
pytest -n auto
```

### Run specific test file
```bash
pytest tests/unit/test_schemas.py
```

### Run specific test
```bash
pytest tests/unit/test_schemas.py::TestJob::test_job_creation_minimal
```

### Verbose output
```bash
pytest -vv
```

### Stop on first failure
```bash
pytest -x
```

## Test Categories

### Unit Tests (Fast, ~1-5s)
- Schema validation (Pydantic models)
- Model configurations
- Configuration file loading
- Template handling

**Coverage Goal:** 95%+

### Integration Tests (Medium, ~5-30s)
- Auto classes (AutoScaffold, AutoEnvironment, AutoWorkflow)
- Dynamic loading from built-in modules
- Dynamic loading from local paths
- Component interfaces

**Coverage Goal:** 85%+

### End-to-End Tests (Slow, ~30s-2m)
- Complete Job creation
- Job → Workflow pipeline
- Serialization/deserialization
- Full system integration

**Coverage Goal:** 75%+

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests (>10s)

## Mocking

Tests use `pytest-mock` for mocking external dependencies:

- HuggingFace dataset loading (`datasets.load_dataset`)
- OSS dataset loading (`ossdata.Dataset.load`)
- Git operations (when testing without network)
- Hera workflow submission

## Fixtures

Common fixtures are defined in `conftest.py`:

- `sample_job` - Complete Job with all components
- `sample_model` - LiteLLMModel instance
- `sample_scaffold` - Scaffold configuration
- `sample_environment` - Environment configuration
- `sample_workflow` - Workflow configuration
- `sample_runtime` - Runtime configuration
- `frozen_time` - Frozen time for timestamp testing
- `tmp_path` - Temporary directory (pytest built-in)

## Coverage Goals

Overall coverage target: **80%+**

By component:
- Schemas: 95%+
- Auto classes: 85%+
- Base classes: 80%+
- Concrete implementations: 75%+

## CI/CD Integration

Recommended GitHub Actions workflow:

```yaml
- name: Run tests
  run: |
    pytest --cov=interaxions --cov-report=xml --cov-report=term-missing
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Writing New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Test Structure (AAA Pattern)
```python
def test_something():
    # Arrange - Set up test data
    job = Job(...)
    
    # Act - Perform the action
    result = job.model_dump_json()
    
    # Assert - Verify the result
    assert "expected" in result
```

### Using Fixtures
```python
def test_with_fixture(sample_job):
    # sample_job is automatically injected
    assert sample_job.name == "test-job"
```

### Parametrized Tests
```python
@pytest.mark.parametrize("source", ["hf", "oss"])
def test_multiple_sources(source):
    env = Environment(..., source=source)
    assert env.source == source
```

## Troubleshooting

### Tests failing due to network issues
Make sure external dependencies are mocked:
```python
def test_something(mocker):
    mocker.patch("datasets.load_dataset")
    # Your test code
```

### Import errors
Ensure the package is installed in development mode:
```bash
pip install -e ".[dev]"
```

### Coverage too low
Check which lines are not covered:
```bash
pytest --cov=interaxions --cov-report=term-missing
```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [Pydantic testing guide](https://docs.pydantic.dev/latest/concepts/testing/)

