"""
Interaxions - A framework for agent interactions in verifiable environments.

This framework provides:
- AutoScaffold: Dynamic loader for scaffold task executors from repositories
- AutoEnvironment: Dynamic loader for environment task executors from repositories
- AutoWorkflow: Dynamic loader for workflow orchestrators from repositories
- IX_HOME cache system for external resources
"""

from interaxions.hub import AutoScaffold, AutoEnvironment, AutoWorkflow
from interaxions.schemas import XJob

__version__ = "0.0.9"

__all__ = [
    "__version__",
    "AutoScaffold",
    "AutoEnvironment",
    "AutoWorkflow",
    "XJob",
]
