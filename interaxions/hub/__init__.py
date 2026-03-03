"""
Hub module for dynamic loading and version management.

Provides Auto classes for loading scaffolds, environments, and workflows
from remote or local repositories. All repos must follow the ix-hub convention:
- config.yaml (with repo_type: scaffold | environment | workflow)
- ix.py       (with exactly one class inheriting from the appropriate Base class)

Environment Variables:
    IX_HOME: Base directory for Interaxions data (default: ~/.interaxions)
    IX_HUB_CACHE: Hub cache directory (default: $IX_HOME/hub)
"""

from interaxions.hub.auto import AutoScaffold, AutoEnvironment, AutoWorkflow
from interaxions.hub.hub_manager import HubManager
from interaxions.hub.constants import (
    IX_HOME,
    HUB_CACHE_DIR,
    get_ix_home,
    get_hub_cache_dir,
)

__all__ = [
    "AutoScaffold",
    "AutoEnvironment",
    "AutoWorkflow",
    "HubManager",
    "IX_HOME",
    "HUB_CACHE_DIR",
    "get_ix_home",
    "get_hub_cache_dir",
]
