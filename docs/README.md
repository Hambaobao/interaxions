# Documentation

## Quick Links

- [Repository Standards](REPOSITORY_STANDARDS.md) - Requirements for creating compatible repositories

## Overview

Interaxions provides a dynamic loading system for agents and environments, similar to HuggingFace Transformers.

### Key Concepts

**Scaffold**: Executes tasks in environments
- Load: `AutoScaffold.from_repo(repo_path)`
- Returns: Scaffold instance
- Method: `scaffold.create_task(job, **kwargs) -> Task`

**Environment**: Provides task contexts
- Load: `AutoEnvironmentFactory.from_repo(repo_path)`
- Returns: Factory instance
- Get instance: `factory.get_from_oss(...)` or `factory.get_from_hf(...)`
- Method: `env.create_task(predictions_path=..., **kwargs) -> Task`

### Loading Priority

1. **Builtin** - Packaged in `interaxions` (e.g., `"swe-agent"`)
2. **Local** - In filesystem (e.g., `"./my-agent"`, `"ix-hub/swe-agent"`)
3. **Remote** - From Git (e.g., `"username/repo"`)

### Environment Variables

- `IX_HOME` - Cache root (default: `~/.interaxions`)
- `IX_ENDPOINT` - Git service URL (default: `https://github.com`)
- `IX_OFFLINE` - Disable remote (default: `false`)

## See Also

- [Main README](../README.md) - Project overview
- [Repository Standards](REPOSITORY_STANDARDS.md) - Complete specifications
