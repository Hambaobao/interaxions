"""
Interaxions - A framework for agent interactions in verifiable environments.

This framework provides:
- AutoScaffold: Dynamic loader for scaffolds from local repositories or hub
- AutoEnvironment: Convenient loader for single environment instances
- AutoEnvironmentFactory: Dynamic loader for environment factories from local repositories or hub
- AutoWorkflow: Dynamic loader for workflows from local repositories or hub
- IX_HOME cache system for external resources
"""

from interaxions.hub import AutoScaffold, AutoEnvironment, AutoEnvironmentFactory, AutoWorkflow
from interaxions.schemas import XJob

__version__ = "0.0.6"

__all__ = [
    "__version__",
    "AutoScaffold",
    "AutoEnvironment",
    "AutoEnvironmentFactory",
    "AutoWorkflow",
    "XJob",
]
