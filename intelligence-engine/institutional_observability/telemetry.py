"""Observability middleware — observes every request; never alters execution (PRP-03)."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from institutional_observability.flags import is_enabled, middleware_enabled
from institutional_observability.logging import log_event
from institutional_observability.metrics import incr, observe_latency
from institutional_observability.models import InstitutionalObservabilityContext
from institutional_observability.tracing import end_span, end_trace, start_span, start_trace


def build_observability_context(
    *,
    correlation_id: str = "",
    request_source: str = "api",
    trace_id: str = "",
) -> InstitutionalObservabilityContext:
    return InstitutionalObservabilityContext(
        trace_id=trace_id or "",
        correlation_id=correlation_id or "",
        request_start=time.time(),
        request_source=request_source,
        diagnostics={"changes_platform_behavior": False},
    )


def begin_request(
    payload: Optional[dict[str, Any]] = None,
    *,
    name: str = "request",
    request_source: str = "api",
) -> dict[str, Any]:
    """Start trace + observability context. Soft no-op when disabled."""
    body = dict(payload or {})
    if not is_enabled() or not middleware_enabled():
        return {"enabled": False, "observability_context": None}

    # Prefer PRP-02 correlation ID
    correlation_id = str(
        body.get("correlation_id")
        or (body.get("security_context") or {}).get("correlation_id")
        or (body.get("_prp_security_gate") or {}).get("correlation_id")
        or ""
    )
    if not correlation_id:
        try:
            from institutional_security.correlation import attach_correlation

            correlation_id = attach_correlation(body)
        except Exception:
            from institutional_observability.tracing import new_trace_id

            correlation_id = f"corr_{new_trace_id()[3:]}"

    started = start_trace(
        correlation_id=correlation_id,
        request_source=request_source,
        name=name,
    )
    ctx = build_observability_context(
        correlation_id=correlation_id,
        request_source=request_source,
        trace_id=started["trace_id"],
    )
    log_event(
        f"begin {name}",
        component="observability",
        severity="info",
        correlation_id=correlation_id,
        trace_id=started["trace_id"],
        tenant_id=str(body.get("tenant_id") or (body.get("security_context") or {}).get("tenant_id") or ""),
        portfolio_id=str(body.get("portfolio_id") or ""),
        user_id=str(body.get("user_id") or (body.get("security_context") or {}).get("user_id") or ""),
        workspace_id=str(body.get("workspace_id") or ""),
    )
    incr("request_count", 1.0, labels={"component": name})
    return {
        "enabled": True,
        "trace_id": started["trace_id"],
        "root_span_id": started["root_span_id"],
        "correlation_id": correlation_id,
        "observability_context": ctx.to_dict(),
        "t0": time.perf_counter(),
    }


def span(trace_id: str, name: str, *, parent_span_id: str = "", **attrs: Any) -> Optional[str]:
    if not trace_id:
        return None
    return start_span(trace_id, name, parent_span_id=parent_span_id, attributes=attrs)


def finish_span(trace_id: str, span_id: Optional[str], *, outcome: str = "ok") -> None:
    if trace_id and span_id:
        end_span(trace_id, span_id, outcome=outcome)


def end_request(
    handle: Optional[dict[str, Any]],
    *,
    outcome: str = "ok",
    component: str = "api",
    result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """End trace, emit metrics/logs, attach observability envelope — does not mutate meaning."""
    out = dict(result or {})
    if not handle or not handle.get("enabled"):
        return out
    tid = str(handle.get("trace_id") or "")
    t0 = float(handle.get("t0") or time.perf_counter())
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    observe_latency(elapsed_ms, component=component)
    if outcome != "ok":
        incr("api_errors", 1.0, labels={"component": component})
    trace = end_trace(tid, outcome=outcome)
    log_event(
        f"end {component} outcome={outcome}",
        component="observability",
        severity="info" if outcome == "ok" else "warning",
        correlation_id=str(handle.get("correlation_id") or ""),
        trace_id=tid,
        extra={"duration_ms": round(elapsed_ms, 3)},
    )
    out["observability_context"] = handle.get("observability_context")
    out["trace_id"] = tid
    if not out.get("correlation_id"):
        out["correlation_id"] = handle.get("correlation_id")
    out["observability"] = {
        "workstream_id": "PRP-03",
        "duration_ms": round(elapsed_ms, 3),
        "outcome": outcome,
        "trace": trace.to_dict() if trace else None,
        "changes_platform_behavior": False,
    }
    return out


def observe_call(
    name: str,
    fn: Callable[[], Any],
    *,
    payload: Optional[dict[str, Any]] = None,
    request_source: str = "api",
) -> Any:
    """
    Run fn() unchanged; wrap with begin/end observability.
    Exceptions propagate — observability never swallows business errors.
    """
    handle = begin_request(payload, name=name, request_source=request_source)
    span_id = span(str(handle.get("trace_id") or ""), name)
    try:
        result = fn()
        outcome = "ok"
        if isinstance(result, dict) and (result.get("ok") is False or result.get("rejected")):
            outcome = "rejected"
        finish_span(str(handle.get("trace_id") or ""), span_id, outcome=outcome)
        if isinstance(result, dict):
            return end_request(handle, outcome=outcome, component=name, result=result)
        end_request(handle, outcome=outcome, component=name, result={})
        return result
    except Exception:
        finish_span(str(handle.get("trace_id") or ""), span_id, outcome="error")
        end_request(handle, outcome="error", component=name, result={})
        raise


def attach_platform_spans(handle: dict[str, Any], stages: list[str]) -> list[str]:
    """Record named platform stages (auth → uag → …) as child spans."""
    tid = str(handle.get("trace_id") or "")
    ids = []
    for stage in stages:
        sid = span(tid, stage)
        if sid:
            finish_span(tid, sid, outcome="ok")
            ids.append(sid)
    return ids
