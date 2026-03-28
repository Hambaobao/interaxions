"""
Interaxions - A framework for composable agent workflows.

This framework provides:
- AutoWorkflow: Dynamic loader for workflow orchestrators from repositories
- AutoTask: Dynamic loader for task executors from repositories
- Job: Job specification schema (workflow + runtime configuration)
- IX_HOME cache system for external resources
"""

from interaxions.hub import AutoWorkflow, AutoTask
from interaxions.schemas import Job

__version__ = "0.0.12"

__all__ = [
    "__version__",
    "AutoWorkflow",
    "AutoTask",
    "Job",
]
