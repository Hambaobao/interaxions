"""
Interaxions - A framework for agent interactions in verifiable environments.

This framework provides:
- AutoAgent: Dynamic loader for agents from local repositories or hub
- AutoEnvironmentFactory: Dynamic loader for environment factories from local repositories or hub
- IX_HOME cache system for external resources
"""

from interaxions.hub import AutoAgent, AutoEnvironmentFactory

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "AutoAgent",
    "AutoEnvironmentFactory",
]
