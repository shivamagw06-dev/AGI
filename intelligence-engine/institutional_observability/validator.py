"""Operational quality gates — generate alerts, never affect business logic (PRP-03)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_observability.alerts import _emit
from institutional_observability.logging import validate_log_fields
from institutional_observability.tracing import validate_span_hierarchy


def validate_trace(trace: dict[str, Any]) -> dict[str, Any]:
    errors = validate_span_hierarchy(trace or {})
    return {"ok": not errors, "errors": errors, "affects_business_logic": False}


def validate_metrics_emitted(snapshot: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if snapshot.get("request_count") is None:
        errors.append("metrics not emitted: request_count")
    if snapshot.get("sample_count", 0) == 0 and not snapshot.get("request_count"):
        errors.append("metrics not emitted: empty series")
    return {"ok": not errors, "errors": errors, "affects_business_logic": False}


def validate_health_freshness(health: dict[str, Any]) -> dict[str, Any]:
    stale = list(health.get("stale_checks") or [])
    errors = [f"health endpoint stale: {s}" for s in stale]
    return {"ok": not errors, "errors": errors, "affects_business_logic": False}


def validate_log(row: dict[str, Any]) -> dict[str, Any]:
    errors = validate_log_fields(row or {})
    return {"ok": not errors, "errors": errors, "affects_business_logic": False}


def run_operational_gates(
    *,
    trace: Optional[dict[str, Any]] = None,
    metrics: Optional[dict[str, Any]] = None,
    health: Optional[dict[str, Any]] = None,
    log_row: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Flag operational issues as alerts — does not reject business requests."""
    findings = []
    if trace is not None:
        v = validate_trace(trace)
        if not v["ok"]:
            findings.extend(v["errors"])
            _emit("dependency_unavailable", "info", f"Trace gate: {v['errors'][:1]}", meta=v)
    if metrics is not None:
        v = validate_metrics_emitted(metrics)
        if not v["ok"]:
            findings.extend(v["errors"])
    if health is not None:
        v = validate_health_freshness(health)
        if not v["ok"]:
            findings.extend(v["errors"])
    if log_row is not None:
        v = validate_log(log_row)
        if not v["ok"]:
            findings.extend(v["errors"])
    return {
        "ok": not findings,
        "findings": findings,
        "affects_business_logic": False,
        "changes_platform_behavior": False,
    }
