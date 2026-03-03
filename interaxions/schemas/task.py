from typing import Any, Dict

from pydantic import BaseModel, Field


class Environment(BaseModel):
    """
    A loaded environment instance, returned by BaseEnvironment.get(id).

    This is a pure data carrier — no loading logic, no task creation logic.
    The workflow receives this object and can either use env.data directly,
    or convert it to a workflow-specific typed domain object.

    Fields:
        id:   The environment instance identifier (e.g., "django__django-12345")
        type: The environment type (e.g., "swe-bench"), matches config.yaml type field
        data: All instance-specific data loaded from the data source.
              The structure of data is defined by the environment repo maintainer.

    Example:
        >>> env: Environment = env_task.get("django__django-12345")
        >>> env.id
        'django__django-12345'
        >>> env.type
        'swe-bench'
        >>> env.data["problem_statement"]
        'Fix the bug in ...'

        >>> # Convert to workflow-specific typed domain object
        >>> swe_env = SWEEnvironment.from_environment(env)
    """

    id: str = Field(..., description="Environment instance identifier")
    type: str = Field(..., description="Environment type, matches repo config.yaml type field")
    data: Dict[str, Any] = Field(default_factory=dict, description="Instance-specific data loaded from the data source")

