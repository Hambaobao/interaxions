"""
Constants for the Interaxions hub module.

Similar to transformers.utils.constants, this module defines default paths
and environment variable names used throughout the hub system.
"""

import os

from pathlib import Path

# Environment variable names (similar to transformers)
ENV_VARS_TRUE_VALUES = {"1", "ON", "YES", "TRUE"}
ENV_VARS_TRUE_AND_AUTO_VALUES = ENV_VARS_TRUE_VALUES.union({"AUTO"})

# Cache directory environment variables
IX_HOME_ENV = "IX_HOME"
IX_HUB_CACHE_ENV = "IX_HUB_CACHE"

# Default directories
DEFAULT_IX_HOME = Path.home() / ".interaxions"
DEFAULT_HUB_CACHE = DEFAULT_IX_HOME / "hub"


def get_ix_home() -> Path:
    """
    Get the base directory for Interaxions data.
    
    Similar to HF_HOME in transformers.
    
    Priority:
    1. IX_HOME environment variable
    2. ~/.interaxions (default)
    
    Returns:
        Base directory path.
    """
    return Path(os.environ.get(IX_HOME_ENV, DEFAULT_IX_HOME))


def get_hub_cache_dir() -> Path:
    """
    Get the cache directory for hub modules.
    
    Similar to default_cache_path in transformers.
    
    Priority:
    1. IX_HUB_CACHE environment variable (most specific)
    2. IX_HOME/hub (if IX_HOME is set)
    3. ~/.interaxions/hub (default)
    
    Returns:
        Cache directory path.
    """
    if IX_HUB_CACHE_ENV in os.environ:
        return Path(os.environ[IX_HUB_CACHE_ENV])

    return get_ix_home() / "hub"


# Expose commonly used values
IX_HOME = get_ix_home()
HUB_CACHE_DIR = get_hub_cache_dir()
