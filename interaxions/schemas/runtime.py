from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field



class TTLConfig(BaseModel):
    """
    TTL (time-to-live) configuration for workflow cleanup.

    Maps directly to Hera's TTLStrategy.

    Example:
        TTLConfig(seconds_after_success=60, seconds_after_failure=1800)
    """

    seconds_after_finished: Optional[int] = Field(
        default=None,
        description="Cleanup delay after completion (success or failure)",
    )
    seconds_after_success: Optional[int] = Field(
        default=None,
        description="Cleanup delay after successful completion",
    )
    seconds_after_failure: Optional[int] = Field(
        default=None,
        description="Cleanup delay after failed completion",
    )


class BackoffConfig(BaseModel):
    """Exponential backoff settings for retry."""

    duration: str = Field(default="1m", description="Initial backoff duration, e.g. '30s', '1m'")
    factor: int = Field(default=2, description="Backoff multiplier")


class RetryConfig(BaseModel):
    """
    Retry strategy for failed workflow steps.

    Maps directly to Hera's RetryStrategy.

    Example:
        RetryConfig(limit=3, policy="Always", backoff=BackoffConfig(duration="1m", factor=2))
    """

    limit: int = Field(default=3, description="Maximum number of retries")
    policy: str = Field(
        default="Always",
        description="Retry policy: Always | OnFailure | OnError | OnTransientError",
    )
    backoff: Optional[BackoffConfig] = Field(default=None)


class RuntimeConfig(BaseModel):
    """
    Runtime configuration for Kubernetes / Argo Workflows execution.

    Defines infrastructure-level settings that are independent of workflow logic.
    All fields map directly to Hera Workflow constructor parameters.

    Example:
        >>> runtime = RuntimeConfig(
        ...     namespace="experiments",
        ...     service_account="argo-workflow",
        ...     ttl=TTLConfig(seconds_after_success=60, seconds_after_failure=1800),
        ...     retry=RetryConfig(limit=3, backoff=BackoffConfig(duration="1m")),
        ...     pod_gc_strategy="OnWorkflowSuccess",
        ...     labels={"team": "research", "env": "prod"},
        ...     node_selector={"gpu": "true"},
        ... )
    """

    namespace: str = Field(..., description="Kubernetes namespace (required)")
    service_account: Optional[str] = Field(default=None, description="Service account name")
    active_deadline_seconds: Optional[int] = Field(
        default=None, description="Hard deadline for the entire workflow"
    )

    # Cleanup
    ttl: Optional[TTLConfig] = Field(
        default=None, description="TTL configuration for workflow cleanup after completion"
    )

    # Retry
    retry: Optional[RetryConfig] = Field(
        default=None, description="Retry strategy for failed steps"
    )

    # Pod / scheduling settings
    dns_policy: Optional[str] = Field(
        default=None, description="DNS policy for workflow pods, e.g. 'ClusterFirst'"
    )
    pod_gc_strategy: Optional[str] = Field(
        default=None,
        description=(
            "When to delete completed pods: "
            "OnWorkflowSuccess | OnWorkflowCompletion | OnPodSuccess | OnPodCompletion"
        ),
    )
    pod_priority_class_name: Optional[str] = Field(
        default=None, description="PriorityClass name for workflow pods"
    )
    node_selector: Optional[Dict[str, str]] = Field(
        default=None, description="Node selector labels for pod scheduling"
    )
    tolerations: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Kubernetes tolerations for pod scheduling"
    )

    # Metadata
    labels: Optional[Dict[str, str]] = Field(
        default=None, description="Workflow labels (merged with Job.labels)"
    )
    annotations: Optional[Dict[str, str]] = Field(
        default=None, description="Workflow annotations"
    )
