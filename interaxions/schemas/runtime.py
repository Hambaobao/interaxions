from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class Runtime(BaseModel):
    """
    Runtime configuration schema.
    
    Defines Kubernetes/Argo Workflows runtime settings.
    
    Example:
        >>> from interaxions.schemas import Runtime
        >>> 
        >>> runtime = Runtime(
        ...     namespace="experiments",
        ...     service_account="argo-workflow",
        ...     image_pull_policy="Always",
        ...     ttl_seconds_after_finished=3600,
        ...     extra_params={
        ...         "labels": {"env": "prod", "team": "research"},
        ...         "annotations": {"owner": "john@example.com"},
        ...         "node_selector": {"gpu": "true"},
        ...         "tolerations": [{"key": "dedicated", "value": "gpu"}]
        ...     }
        ... )
    """
    namespace: str = Field(..., description="Kubernetes namespace (required)")
    service_account: Optional[str] = Field(None, description="Service account name")
    image_pull_policy: Literal["Always", "IfNotPresent"] = Field(default="IfNotPresent", description="Image pull policy")
    active_deadline_seconds: Optional[int] = Field(None, description="Active deadline seconds")
    ttl_seconds_after_finished: Optional[int] = Field(None, description="TTL (seconds) for workflow cleanup after completion")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional runtime parameters (e.g., labels, annotations, node_selector, tolerations, priority_class_name)")
