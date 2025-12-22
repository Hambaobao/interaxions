"""
Interaxions - A framework for agent interactions in verifiable environments.

This framework provides:
- AutoScaffold: Dynamic loader for scaffolds from local repositories or hub
- AutoEnvironmentFactory: Dynamic loader for environment factories from local repositories or hub
- AutoWorkflow: Dynamic loader for workflows from local repositories or hub
- IX_HOME cache system for external resources
"""

from interaxions.hub import AutoScaffold, AutoEnvironmentFactory, AutoWorkflow
from interaxions.schemas import LiteLLMModel

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "AutoScaffold",
    "AutoEnvironmentFactory",
    "AutoWorkflow",
    "LiteLLMModel",
]
