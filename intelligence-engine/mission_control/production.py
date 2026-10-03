"""Mission Control production facade — snapshot-backed diagnostics (HTTP read-only)."""

from __future__ import annotations

from typing import Any

from mission_control.flags import flags_dict, is_enabled
from mission_control.schema import MISSION_CONTROL_VERSION, PROGRAMME, PROGRAMME_SHORT
from mission_control import snapshot as mc_snapshot
from mission_control import store as mc_store


def health() -> dict[str, Any]:
    meta = mc_snapshot.snapshot_meta()
    job = meta.get("job") or {}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": MISSION_CONTROL_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "read_only": True,
        "not_an_engine": True,
        "not_client_facing": True,
        "never_modifies_research": True,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "agent_map": "GET /v1/mission-control/agent-map",
        "delivery": "snapshot",
        "snapshot": {
            "exists": meta.get("exists"),
            "status": meta.get("status"),
            "lastUpdated": meta.get("persisted_at") or meta.get("last_successful_at"),
            "last_successful_at": meta.get("last_successful_at"),
            "last_failure_at": meta.get("last_failure_at"),
            "last_error": meta.get("last_error"),
            "trigger": meta.get("trigger"),
            "path": meta.get("path"),
        },
        "worker": {
            "job_status": job.get("status"),
            "job_id": job.get("job_id"),
            "job_trigger": job.get("trigger"),
            "queue_status": job.get("status") or "idle",
        },
    }


def agent_map() -> dict[str, Any]:
    """Serve precomputed Agent Map snapshot only. Never probes on the HTTP path."""
    from mission_control.agent_map_snapshot import read_agent_map

    return read_agent_map()


def intelligence_map() -> dict[str, Any]:
    """Serve precomputed Intelligence Map snapshot only. Never probes on the HTTP path."""
    from mission_control.intelligence_map_snapshot import read_intelligence_map

    return read_intelligence_map()


def institutional_intelligence() -> dict[str, Any]:
    """Serve precomputed Institutional Intelligence snapshot only. Never aggregates."""
    from mission_control.institutional_intelligence_snapshot import (
        read_institutional_intelligence,
    )

    return read_institutional_intelligence()


def dashboard(*, ioc_service: Any | None = None, force: bool = False) -> dict[str, Any]:
    """Serve precomputed snapshot only. Never builds on the HTTP path.

    ``force`` and ``ioc_service`` are accepted for API compatibility but ignored
    for computation — use POST /mission-control/rebuild to enqueue a worker build.
    """
    _ = ioc_service
    if force:
        # Never compute inline; queue background rebuild and return current state.
        mc_snapshot.enqueue_rebuild(trigger="dashboard_force_ignored", wait=False)
    return mc_snapshot.read_dashboard()


def rebuild(*, trigger: str = "admin_rebuild", wait: bool = False) -> dict[str, Any]:
    """Queue snapshot rebuild. Returns immediately unless wait=True (tests/ops)."""
    return mc_snapshot.enqueue_rebuild(trigger=trigger, wait=wait)


def acknowledge_alert(alert_id: str, *, actor: str | None = None) -> dict[str, Any]:
    """Acknowledge only — never mutates research / house views."""
    return mc_store.acknowledge(alert_id, actor=actor)


def system_report(*, ioc_service: Any | None = None) -> dict[str, Any]:
    _ = ioc_service
    desk = mc_snapshot.read_dashboard()
    if desk.get("_warming") or desk.get("status") == "warming":
        return {
            "ok": True,
            "status": "warming",
            "report_type": "mission_control_system_report",
            "title": "AGI Mission Control System Report",
            "generated_at": None,
            "version": MISSION_CONTROL_VERSION,
            "read_only": True,
            "message": "Snapshot warming — report unavailable until first snapshot.",
            "sections": {},
        }
    sections = {
        "platform_health": desk.get("executive_status"),
        "api_health": desk.get("api_status"),
        "knowledge_growth": desk.get("knowledge_growth"),
        "coverage": desk.get("coverage_dashboard"),
        "learning": desk.get("academy"),
        "research": desk.get("research_pipeline"),
        "predictions": desk.get("prediction_intelligence"),
        "errors": [
            a for a in (desk.get("alerts_centre") or []) if not a.get("acknowledged")
        ][:40],
        "warnings": [
            p for p in (desk.get("platform_status") or []) if p.get("current_status") == "Warning"
        ],
        "recommendations": [
            "Investigate Critical / Offline platforms first",
            "Acknowledge resolved alerts in Alerts Centre",
            "Review CMS companies needing House View review",
            "Check IOC provider circuits for Red APIs",
        ],
        "architecture_map": desk.get("architecture_map"),
        "deployment": desk.get("deployment_centre"),
    }
    return {
        "ok": True,
        "report_type": "mission_control_system_report",
        "title": "AGI Mission Control System Report",
        "generated_at": desk.get("generated_at"),
        "version": MISSION_CONTROL_VERSION,
        "read_only": True,
        "sections": sections,
        **sections,
    }


def quality_gates() -> dict[str, Any]:
    # Snapshot only — never rebuild for gates.
    desk = mc_snapshot.read_dashboard()
    if desk.get("_warming") or desk.get("status") == "warming":
        return {
            "programme": PROGRAMME,
            "version": MISSION_CONTROL_VERSION,
            "passed": False,
            "status": "warming",
            "criteria": {"snapshot_ready": False},
            "message": "Mission Control snapshot warming",
        }
    criteria = {
        "enabled": desk.get("enabled") is True,
        "read_only": desk.get("read_only") is True,
        "executive_status_present": bool(desk.get("executive_status")),
        "platforms_present": len(desk.get("platform_status") or []) >= 10,
        "engines_present": len(desk.get("engine_status") or []) >= 5,
        "apis_present": len(desk.get("api_status") or []) >= 5,
        "knowledge_growth_present": bool(desk.get("knowledge_growth")),
        "coverage_present": bool(desk.get("coverage_dashboard")),
        "company_monitor_present": bool(desk.get("company_monitor")),
        "architecture_map_present": len((desk.get("architecture_map") or {}).get("nodes") or []) >= 10,
        "events_present": isinstance(desk.get("live_event_stream"), list),
        "copilot_present": bool((desk.get("executive_copilot") or {}).get("prompts")),
        "never_mutates": desk.get("never_modifies_research") is True,
        "snapshot_ready": True,
    }
    passed = all(criteria.values())
    return {
        "programme": PROGRAMME,
        "version": MISSION_CONTROL_VERSION,
        "passed": passed,
        "criteria": criteria,
        "message": "Mission Control quality gates passed" if passed else "Mission Control incomplete",
    }


def ask_observability(*, limit: int = 25) -> dict[str, Any]:
    """Live Ask evidence funnel / latency KPIs from in-process ring buffer."""
    from app.ui.ask_observability_store import kpi_dashboard, recent_traces

    dash = kpi_dashboard()
    return {
        "ok": True,
        "programme": PROGRAMME,
        "layer": "Ask Evidence Intelligence",
        "version": MISSION_CONTROL_VERSION,
        "read_only": True,
        "not_client_facing": True,
        "diagnostics_visibility": "internal",
        **dash,
        "recent_traces": recent_traces(limit=limit),
    }


def reset_for_tests() -> None:
    mc_snapshot.reset_for_tests()
    try:
        from app.ui.ask_observability_store import reset_for_tests as ask_reset

        ask_reset()
    except Exception:
        pass
    mc_store.reset_for_tests()
