"""L-01 production façades — analytics / feedback / flags / SLAs / Launch Center."""

from __future__ import annotations

import time
from typing import Any, Optional

from institutional_launch.analytics.events import emit_event, recent_events
from institutional_launch.analytics.journey import journey_funnel, record_journey_step
from institutional_launch.diagnostics import build_diagnostics
from institutional_launch.feature_flags import list_flags, set_flag
from institutional_launch.feedback import feedback_summary, recent_feedback, submit_feedback
from institutional_launch.flags import flags_dict, is_enabled, journey_tracking_enabled
from institutional_launch.launch_report import build_launch_report, launch_center_board
from institutional_launch.product_metrics import product_dashboard
from institutional_launch.product_metrics.adoption import incr, record_ask
from institutional_launch.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_GENERAL_AVAILABILITY,
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    LAUNCH_ENGINE_VERSION,
    L_PRODUCT,
    L_ROLE,
    L_SPEC,
    L_VERSION,
    L_WORKSTREAM_ID,
)
from institutional_launch.sla import evaluate_slas, sla_targets

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    from institutional_launch.analytics.events import reset_for_tests as reset_events
    from institutional_launch.analytics.journey import reset_for_tests as reset_journey
    from institutional_launch.feature_flags import reset_for_tests as reset_flags
    from institutional_launch.feedback import reset_for_tests as reset_feedback
    from institutional_launch.product_metrics import reset_for_tests as reset_metrics
    from institutional_launch.sla import reset_for_tests as reset_sla

    reset_events()
    reset_journey()
    reset_flags()
    reset_feedback()
    reset_metrics()
    reset_sla()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": L_WORKSTREAM_ID,
        "product": L_PRODUCT,
        "version": L_VERSION,
        "role": L_ROLE,
        "llm": False,
        "is_usage_validation": True,
        "is_feature_expansion": False,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "agib_general_availability": AGIB_GENERAL_AVAILABILITY,
        "launch_engine_version": LAUNCH_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": L_SPEC,
        "brand": "AGI",
        "programme": "Launch",
        "phase": "launch_validation",
        "as_of": now_iso(),
        **launch_center_board(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    board = launch_center_board() if is_enabled() else {"launch_center": False}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": L_WORKSTREAM_ID,
        "product": L_PRODUCT,
        "version": L_VERSION,
        "llm": False,
        **board,
    }


def track_event(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    if not is_enabled():
        return {"ok": False, "enabled": False}
    row = emit_event(
        str(body.get("name") or "custom"),
        user_id=str(body.get("user_id") or ""),
        stage=str(body.get("stage") or ""),
        duration_ms=body.get("duration_ms"),
        ok=bool(body.get("ok", True)),
        error=str(body.get("error") or ""),
        meta=body.get("meta") if isinstance(body.get("meta"), dict) else {},
    )
    return {"ok": True, "workstream_id": L_WORKSTREAM_ID, "event": row}


def track_journey(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    if not is_enabled():
        return {"ok": False, "enabled": False}
    out = record_journey_step(
        str(body.get("stage") or "dashboard"),
        user_id=str(body.get("user_id") or ""),
        session_id=str(body.get("session_id") or ""),
        duration_ms=body.get("duration_ms"),
        ok=bool(body.get("ok", True)),
        error=str(body.get("error") or ""),
        completed=bool(body.get("completed", True)),
        dropped=bool(body.get("dropped", False)),
        meta=body.get("meta") if isinstance(body.get("meta"), dict) else {},
    )
    return {"ok": True, "workstream_id": L_WORKSTREAM_ID, **out}


def metrics_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": L_WORKSTREAM_ID,
        **product_dashboard(),
    }


def funnel_api() -> dict[str, Any]:
    return {"ok": True, "workstream_id": L_WORKSTREAM_ID, **journey_funnel()}


def feedback_submit_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    out = submit_feedback(
        screen=str(body.get("screen") or body.get("surface") or "unknown"),
        reaction=str(body.get("reaction") or body.get("vote") or ""),
        comment=str(body.get("comment") or ""),
        tags=list(body.get("tags") or []),
        user_id=str(body.get("user_id") or ""),
        meta=body.get("meta") if isinstance(body.get("meta"), dict) else {},
    )
    out["workstream_id"] = L_WORKSTREAM_ID
    return out


def feedback_list_api(limit: int = 40) -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": L_WORKSTREAM_ID,
        "summary": feedback_summary(),
        "feedback": recent_feedback(limit=limit),
    }


def flags_api() -> dict[str, Any]:
    return {"ok": True, "workstream_id": L_WORKSTREAM_ID, **list_flags()}


def flag_set_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    out = set_flag(
        str(body.get("flag") or body.get("name") or ""),
        bool(body.get("enabled")),
        actor=str(body.get("actor") or body.get("user_id") or ""),
    )
    out["workstream_id"] = L_WORKSTREAM_ID
    return out


def sla_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": L_WORKSTREAM_ID,
        "targets": sla_targets(),
        **evaluate_slas(),
    }


def report_api() -> dict[str, Any]:
    return {"ok": True, "workstream_id": L_WORKSTREAM_ID, "report": build_launch_report()}


def events_api(limit: int = 40) -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": L_WORKSTREAM_ID,
        "events": recent_events(limit=limit),
    }


def diagnostics_api() -> dict[str, Any]:
    return {"ok": True, **build_diagnostics()}


# --- Soft journey hooks (observe usage; never change business meaning) ---


def maybe_track_ask(payload: dict[str, Any], result: dict[str, Any]) -> None:
    if not is_enabled() or not journey_tracking_enabled():
        return
    try:
        user_id = str(
            payload.get("user_id")
            or (payload.get("security_context") or {}).get("user_id")
            or (result.get("security_context") or {}).get("user_id")
            or ""
        )
        session_id = str(payload.get("session_id") or "")
        latency = float(result.get("latency_ms") or 0)
        if not latency and result.get("observability"):
            latency = float((result.get("observability") or {}).get("duration_ms") or 0)
        ok = bool(result.get("ok"))
        sources = 0
        resp = result.get("response") or {}
        if isinstance(resp, dict):
            sources = len(resp.get("sources") or resp.get("execution_plan") or []) or 0
        record_ask(ok=ok, latency_ms=latency, sources=sources)
        record_journey_step(
            "ask_agi",
            user_id=user_id,
            session_id=session_id,
            duration_ms=latency or None,
            ok=ok,
            completed=ok,
            dropped=not ok and result.get("rejected") is True,
        )
    except Exception:
        pass


def maybe_track_workspace(payload: dict[str, Any], result: dict[str, Any], *, kind: str = "company") -> None:
    if not is_enabled() or not journey_tracking_enabled():
        return
    try:
        incr("workspace_sessions")
        if kind == "company":
            incr("companies_viewed")
        incr("research_opened")
        record_journey_step(
            "research_workspace",
            user_id=str(payload.get("user_id") or ""),
            session_id=str(payload.get("session_id") or ""),
            duration_ms=float(result.get("latency_ms") or 0) or None,
            ok=bool(result.get("ok")),
        )
        if kind == "company":
            record_journey_step(
                "company",
                user_id=str(payload.get("user_id") or ""),
                ok=bool(result.get("ok")),
            )
        elif kind == "portfolio":
            record_journey_step(
                "portfolio",
                user_id=str(payload.get("user_id") or ""),
                ok=bool(result.get("ok")),
            )
    except Exception:
        pass


def maybe_track_publication(payload: dict[str, Any], result: dict[str, Any]) -> None:
    if not is_enabled() or not journey_tracking_enabled():
        return
    try:
        ok = bool(result.get("ok") or result.get("async"))
        if ok:
            incr("publications_generated")
        if result.get("distribution") or payload.get("distribute_to"):
            incr("publications_shared")
        if payload.get("export") or (result.get("publication") or {}).get("status") == "exported":
            incr("publications_exported")
            record_journey_step("export", ok=ok, user_id=str(payload.get("user_id") or ""))
        record_journey_step(
            "publication",
            user_id=str(payload.get("user_id") or ""),
            session_id=str(payload.get("session_id") or ""),
            ok=ok,
            duration_ms=float(result.get("latency_ms") or 0) or None,
        )
    except Exception:
        pass


def maybe_track_login(payload: dict[str, Any], result: dict[str, Any]) -> None:
    if not is_enabled() or not journey_tracking_enabled():
        return
    try:
        record_journey_step(
            "login",
            user_id=str((result.get("security_context") or {}).get("user_id") or payload.get("username") or ""),
            session_id=str(result.get("session_id") or ""),
            ok=bool(result.get("ok")),
            completed=bool(result.get("ok")),
            dropped=not bool(result.get("ok")),
        )
        if result.get("ok"):
            record_journey_step(
                "dashboard",
                user_id=str((result.get("security_context") or {}).get("user_id") or ""),
                session_id=str(result.get("session_id") or ""),
                ok=True,
            )
    except Exception:
        pass
