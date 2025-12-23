"""
Hub module for dynamic loading and version management.

Similar to HuggingFace transformers, this module provides:
- Dynamic loading of agents and environments from repositories
- Version management (tag, branch, commit)
- Caching of loaded modules
- Auto classes for convenient loading

Environment Variables:
    IX_HOME: Base directory for Interaxions data (default: ~/.interaxions)
    IX_HUB_CACHE: Hub cache directory (default: $IX_HOME/hub)
"""

from interaxions.hub.auto import AutoScaffold, AutoEnvironment, AutoEnvironmentFactory, AutoWorkflow
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
    "AutoEnvironmentFactory",
    "AutoWorkflow",
    "HubManager",
    "IX_HOME",
    "HUB_CACHE_DIR",
    "get_ix_home",
    "get_hub_cache_dir",
]
