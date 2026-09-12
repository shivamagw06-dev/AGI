"""PRP-03 core observability objects — third context alongside Execution + Security."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class InstitutionalObservabilityContext:
    """How the request is tracked. Never mutates execution or security meaning."""

    trace_id: str
    correlation_id: str
    request_start: float
    request_source: str = "api"
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "request_start": self.request_start,
            "request_source": self.request_source,
            "diagnostics": dict(self.diagnostics or {}),
            "immutable": True,
            "changes_platform_behavior": False,
            "complements_execution_and_security": True,
        }


@dataclass(frozen=True)
class InstitutionalSpan:
    span_id: str
    name: str
    parent_span_id: str = ""
    start_ms: float = 0.0
    end_ms: float = 0.0
    outcome: str = "ok"
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "parent_span_id": self.parent_span_id or None,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": round(max(0.0, self.end_ms - self.start_ms), 3),
            "outcome": self.outcome,
            "attributes": dict(self.attributes or {}),
        }


@dataclass(frozen=True)
class InstitutionalTrace:
    trace_id: str
    correlation_id: str
    spans: tuple[InstitutionalSpan, ...] = ()
    duration_ms: float = 0.0
    outcome: str = "ok"
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "spans": [s.to_dict() for s in self.spans],
            "duration_ms": round(self.duration_ms, 3),
            "outcome": self.outcome,
            "diagnostics": dict(self.diagnostics or {}),
            "span_count": len(self.spans),
        }


@dataclass(frozen=True)
class InstitutionalMetric:
    metric_name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "labels": dict(self.labels or {}),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class InstitutionalHealth:
    service: str
    status: str
    latency_ms: Optional[float] = None
    dependencies: tuple[str, ...] = ()
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "dependencies": list(self.dependencies),
            "diagnostics": dict(self.diagnostics or {}),
        }
