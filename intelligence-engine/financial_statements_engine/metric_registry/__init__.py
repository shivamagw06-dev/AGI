"""FSE-03 Metric Registry — versioned canonical metric service."""

from financial_statements_engine.metric_registry.production import health, metrics_payload, resolve_payload
from financial_statements_engine.metric_registry.schema import REGISTRY_VERSION, WORKSTREAM_ID
from financial_statements_engine.metric_registry.service import (
    assert_canonical,
    get_metric,
    is_canonical,
    list_metrics,
    resolve,
    resolve_required,
    to_normalized_value,
)

__all__ = [
    "REGISTRY_VERSION",
    "WORKSTREAM_ID",
    "health",
    "metrics_payload",
    "resolve_payload",
    "resolve",
    "resolve_required",
    "get_metric",
    "list_metrics",
    "is_canonical",
    "assert_canonical",
    "to_normalized_value",
]
