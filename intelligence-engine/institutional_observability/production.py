"""PRP-03 production façades — ops health / metrics / traces / Operations Center."""

from __future__ import annotations

from typing import Any, Optional

from institutional_observability import alerts as alerts_mod
from institutional_observability import health as health_mod
from institutional_observability import logging as log_mod
from institutional_observability import metrics as metrics_mod
from institutional_observability import tracing as tracing_mod
from institutional_observability.dashboards import operations_center_board
from institutional_observability.dependency_monitor import probe_dependencies
from institutional_observability.diagnostics import build_diagnostics
from institutional_observability.flags import flags_dict, is_enabled
from institutional_observability.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    OBS_ENGINE_VERSION,
    PRP_PRODUCT,
    PRP_ROLE,
    PRP_SPEC,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
)
from institutional_observability.service_map import build_service_map
from institutional_observability.telemetry import (
    attach_platform_spans,
    begin_request,
    end_request,
    finish_span,
    span,
)
from institutional_observability.validator import run_operational_gates

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    tracing_mod.reset_for_tests()
    metrics_mod.reset_for_tests()
    log_mod.reset_for_tests()
    alerts_mod.reset_for_tests()
    health_mod.reset_for_tests()


def health() -> dict[str, Any]:
    agg = health_mod.aggregate_health() if is_enabled() else {"status": "disabled"}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "role": PRP_ROLE,
        "llm": False,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "obs_engine_version": OBS_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "changes_platform_behavior": False,
        "enters_intelligence_layer": False,
        "complements_execution_and_security": True,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PRP_SPEC,
        "brand": "AGI",
        "programme": "PRP",
        "phase": "production_readiness",
        "as_of": now_iso(),
        "platform_health": agg,
        "liveness": health_mod.liveness(),
        "readiness": health_mod.readiness() if is_enabled() else {"status": "not_ready"},
    }


def soft_slice_mission_control() -> dict[str, Any]:
    board = operations_center_board() if is_enabled() else {"operations_center": False}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "llm": False,
        "operations_center": True,
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "changes_platform_behavior": False,
        "enters_intelligence_layer": False,
        **board,
    }


def ops_health() -> dict[str, Any]:
    h = health()
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        **(h.get("platform_health") or {}),
        "liveness": h.get("liveness"),
        "readiness": h.get("readiness"),
    }


def ops_metrics() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "metrics": metrics_mod.snapshot(),
        "recent": metrics_mod.recent_metrics(40),
        "changes_platform_behavior": False,
    }


def ops_trace(trace_id: str) -> dict[str, Any]:
    row = tracing_mod.get_trace(trace_id)
    if not row:
        return {"ok": False, "error": "trace_not_found", "trace_id": trace_id}
    gates = run_operational_gates(trace=row)
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "trace": row,
        "operational_gates": gates,
    }


def ops_service_map() -> dict[str, Any]:
    return {"ok": True, "workstream_id": PRP_WORKSTREAM_ID, **build_service_map()}


def ops_alerts() -> dict[str, Any]:
    alerts_mod.evaluate()
    return {"ok": True, "workstream_id": PRP_WORKSTREAM_ID, **alerts_mod.alert_metrics()}


def ops_dependencies() -> dict[str, Any]:
    return {"ok": True, "workstream_id": PRP_WORKSTREAM_ID, **probe_dependencies()}


def ops_logs(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "logs": log_mod.recent_logs(
            limit=int(body.get("limit") or 50),
            severity=str(body.get("severity") or ""),
            correlation_id=str(body.get("correlation_id") or ""),
            component=str(body.get("component") or ""),
        ),
    }


def diagnostics_api() -> dict[str, Any]:
    return {"ok": True, **build_diagnostics()}


# --- Soft middleware helpers for platform façades (observe only) ---


def maybe_begin(payload: dict[str, Any], *, name: str) -> Optional[dict[str, Any]]:
    if not is_enabled():
        return None
    handle = begin_request(payload, name=name, request_source="platform")
    if not handle.get("enabled"):
        return None
    # Record standard pipeline stages as empty-duration markers when observability starts
    stages = ["authentication", "authorization", name]
    attach_platform_spans(handle, stages)
    payload["_prp_obs_handle"] = handle
    return handle


def maybe_span(payload: dict[str, Any], name: str) -> Optional[str]:
    handle = payload.get("_prp_obs_handle")
    if not isinstance(handle, dict):
        return None
    return span(str(handle.get("trace_id") or ""), name)


def maybe_end(
    payload: dict[str, Any],
    result: dict[str, Any],
    *,
    component: str,
) -> dict[str, Any]:
    handle = payload.get("_prp_obs_handle")
    if not isinstance(handle, dict):
        return result
    outcome = "ok"
    if result.get("ok") is False or result.get("rejected"):
        outcome = "rejected"
    if result.get("error") and result.get("ok") is False:
        outcome = "error"
    # Sync auth failures into metrics when security denied
    if result.get("error") == "authentication_failed":
        metrics_mod.incr("authentication_failures", 1.0)
    return end_request(handle, outcome=outcome, component=component, result=result)


def record_publication_duration(ms: float) -> None:
    metrics_mod.emit("publication_duration_ms", ms, labels={"component": "pub"})


def record_workspace_load(ms: float) -> None:
    metrics_mod.emit("workspace_load_ms", ms, labels={"component": "rw"})


def record_graph_update(ms: float) -> None:
    metrics_mod.emit("graph_update_ms", ms, labels={"component": "graph"})


def record_background_job() -> None:
    metrics_mod.incr("background_jobs", 1.0)
