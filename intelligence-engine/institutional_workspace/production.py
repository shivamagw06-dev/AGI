"""RW-01 production façades — workspace APIs / Mission Control Workspace Health."""

from __future__ import annotations

import time
from typing import Any, Optional

from institutional_workspace.diagnostics import workspace_health_board
from institutional_workspace.flags import flags_dict, is_enabled
from institutional_workspace.navigation import search_workspace
from institutional_workspace import notes as notes_mod
from institutional_workspace.object_viewer import view_object
from institutional_workspace.schema import (
    RW_PRODUCT,
    RW_ROLE,
    RW_SPEC,
    RW_VERSION,
    RW_WORKSTREAM_ID,
    WORKSPACE_ENGINE_VERSION,
)
from institutional_workspace.workspace import (
    assemble_committee_workspace,
    assemble_company_workspace,
    assemble_portfolio_workspace,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_CACHE: dict[str, Any] = {}


def reset_for_tests() -> None:
    _CACHE.clear()
    notes_mod.reset_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": RW_WORKSTREAM_ID,
        "product": RW_PRODUCT,
        "version": RW_VERSION,
        "role": RW_ROLE,
        "llm": False,
        "generates_recommendations": False,
        "mutates_system_intelligence": False,
        "presentation_only": True,
        "notes_are_analyst_owned": True,
        "workspace_engine_version": WORKSPACE_ENGINE_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": RW_SPEC,
        "brand": "AGI",
        "phase": 5,
        "notes": notes_mod.notes_metrics(),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    rows = list(_CACHE.values())
    board = workspace_health_board(rows)
    return {
        "status": h.get("status"),
        "workstream_id": RW_WORKSTREAM_ID,
        "product": RW_PRODUCT,
        "version": RW_VERSION,
        "llm": False,
        "workspace_health": True,
        **board,
    }


def get_company_workspace(
    ticker: str,
    *,
    focus: str = "overview",
    security: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": RW_WORKSTREAM_ID}
    sec_body = dict(security or {})
    # PRP-03: Observability middleware — observe only
    try:
        from institutional_observability.production import maybe_begin

        maybe_begin(sec_body, name="rw.workspace")
    except Exception:
        pass

    # PRP-02: Security Gateway before workspace assemble
    try:
        from institutional_security.production import finalize_with_security, maybe_gate_workspace

        denied = maybe_gate_workspace(sec_body)
        if denied is not None:
            try:
                from institutional_observability.production import maybe_end

                return maybe_end(sec_body, denied, component="rw.workspace")
            except Exception:
                return denied
    except Exception:
        pass

    t0 = time.perf_counter()
    # PRP-01: workspace cache (target < 1s)
    try:
        from institutional_performance.production import (
            maybe_get_workspace_cache,
            record_op_latency,
        )

        cached = maybe_get_workspace_cache("company", str(ticker).upper(), focus)
        if isinstance(cached, dict) and cached.get("ok"):
            elapsed = time.perf_counter() - t0
            record_op_latency("workspace", elapsed, cached=True)
            out = dict(cached)
            out["cached"] = True
            out["cache_layer"] = "PRP-01"
            out["latency_ms"] = round(elapsed * 1000.0, 2)
            try:
                from institutional_security.production import finalize_with_security

                out = finalize_with_security(out, sec_body)
            except Exception:
                pass
            try:
                from institutional_observability.production import maybe_end, record_workspace_load

                record_workspace_load(elapsed * 1000.0)
                return maybe_end(sec_body, out, component="rw.workspace")
            except Exception:
                return out
    except Exception:
        pass

    ws = assemble_company_workspace(ticker, focus=focus)
    _CACHE[ws.workspace_id] = ws
    result = {
        "ok": True,
        "workstream_id": RW_WORKSTREAM_ID,
        "workspace": ws.to_dict(),
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "mutates_system_intelligence": False,
        "presentation_only": True,
        "cached": False,
    }
    try:
        from institutional_performance.production import (
            maybe_set_workspace_cache,
            record_op_latency,
        )

        record_op_latency("workspace", time.perf_counter() - t0, cached=False)
        maybe_set_workspace_cache("company", str(ticker).upper(), focus, value=result)
    except Exception:
        pass
    try:
        from institutional_security.production import finalize_with_security

        result = finalize_with_security(result, sec_body)
    except Exception:
        pass
    try:
        from institutional_observability.production import maybe_end, record_workspace_load

        record_workspace_load(float(result.get("latency_ms") or 0))
        result = maybe_end(sec_body, result, component="rw.workspace")
    except Exception:
        pass
    try:
        from institutional_launch.production import maybe_track_workspace

        maybe_track_workspace(sec_body, result, kind="company")
    except Exception:
        pass
    return result


def get_portfolio_workspace(
    portfolio_id: str = "agi-core-equity",
    *,
    focus: str = "overview",
    security: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": RW_WORKSTREAM_ID}
    sec_body = dict(security or {})
    sec_body.setdefault("portfolio_id", portfolio_id)
    try:
        from institutional_security.production import finalize_with_security, maybe_gate_workspace

        denied = maybe_gate_workspace(sec_body)
        if denied is not None:
            return denied
    except Exception:
        pass

    t0 = time.perf_counter()
    try:
        from institutional_performance.production import (
            maybe_get_workspace_cache,
            record_op_latency,
        )

        cached = maybe_get_workspace_cache("portfolio", str(portfolio_id), focus)
        if isinstance(cached, dict) and cached.get("ok"):
            elapsed = time.perf_counter() - t0
            record_op_latency("workspace", elapsed, cached=True)
            out = dict(cached)
            out["cached"] = True
            out["cache_layer"] = "PRP-01"
            out["latency_ms"] = round(elapsed * 1000.0, 2)
            try:
                from institutional_security.production import finalize_with_security

                return finalize_with_security(out, sec_body)
            except Exception:
                return out
    except Exception:
        pass

    ws = assemble_portfolio_workspace(portfolio_id, focus=focus)
    _CACHE[ws.workspace_id] = ws
    result = {
        "ok": True,
        "workstream_id": RW_WORKSTREAM_ID,
        "workspace": ws.to_dict(),
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "mutates_system_intelligence": False,
        "presentation_only": True,
        "cached": False,
    }
    try:
        from institutional_performance.production import (
            maybe_set_workspace_cache,
            record_op_latency,
        )

        record_op_latency("workspace", time.perf_counter() - t0, cached=False)
        maybe_set_workspace_cache("portfolio", str(portfolio_id), focus, value=result)
    except Exception:
        pass
    try:
        from institutional_security.production import finalize_with_security

        return finalize_with_security(result, sec_body)
    except Exception:
        return result


def get_committee_workspace() -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": RW_WORKSTREAM_ID}
    ws = assemble_committee_workspace()
    _CACHE[ws.workspace_id] = ws
    return {
        "ok": True,
        "workstream_id": RW_WORKSTREAM_ID,
        "workspace": ws.to_dict(),
        "mutates_system_intelligence": False,
    }


def get_timeline(subject_id: str, *, context: str = "company") -> dict[str, Any]:
    if context == "portfolio":
        result = get_portfolio_workspace(subject_id)
    elif context == "committee":
        result = get_committee_workspace()
    else:
        result = get_company_workspace(subject_id)
    if not result.get("ok"):
        return result
    ws = result["workspace"]
    return {
        "ok": True,
        "workstream_id": RW_WORKSTREAM_ID,
        "context": context,
        "subject_id": subject_id,
        "timeline": ws.get("timeline") or [],
        "lineage_hint": [
            "Evidence",
            "Observation",
            "Decision Updated",
            "Risk Changed",
            "Policy Breach",
            "Committee",
        ],
    }


def get_object(object_id: str, *, object_type: str = "", payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    # Resolve from cached workspaces when possible
    for ws in _CACHE.values():
        for o in ws.linked_objects:
            if o.object_id == object_id or (object_type and o.object_type == object_type and object_id in o.object_id):
                return {
                    "ok": True,
                    "workstream_id": RW_WORKSTREAM_ID,
                    "object": view_object(o.object_type, {"title": o.label, "summary": o.summary}, object_id=o.object_id),
                    "href": o.href,
                }
        for e in ws.timeline:
            if e.object_id == object_id or e.event_id == object_id:
                return {
                    "ok": True,
                    "workstream_id": RW_WORKSTREAM_ID,
                    "object": view_object(e.object_type, {"title": e.title, "summary": e.summary}, object_id=e.object_id),
                }
    viewed = view_object(object_type or "Unknown", payload or {}, object_id=object_id)
    return {"ok": True, "workstream_id": RW_WORKSTREAM_ID, "object": viewed, "soft": True}


def search(subject_id: str, query: str, *, context: str = "company") -> dict[str, Any]:
    if context == "portfolio":
        result = get_portfolio_workspace(subject_id)
    else:
        result = get_company_workspace(subject_id)
    if not result.get("ok"):
        return result
    # Re-assemble typed workspace for search helper
    if context == "portfolio":
        ws = assemble_portfolio_workspace(subject_id)
    else:
        ws = assemble_company_workspace(subject_id)
    hits = search_workspace(ws, query)
    return {
        "ok": True,
        "workstream_id": RW_WORKSTREAM_ID,
        "query": query,
        "hits": hits,
        "count": len(hits),
    }


def add_analyst_note(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    context_key = str(body.get("context_key") or "")
    if not context_key:
        ticker = str(body.get("ticker") or "")
        portfolio_id = str(body.get("portfolio_id") or "")
        context_key = f"company:{ticker}" if ticker else f"portfolio:{portfolio_id or 'agi-core-equity'}"
    note = notes_mod.add_note(
        context_key=context_key,
        title=str(body.get("title") or "Untitled note"),
        body=str(body.get("body") or ""),
        tags=tuple(body.get("tags") or ()),
        linked_decision_id=str(body.get("linked_decision_id") or ""),
        linked_object_id=str(body.get("linked_object_id") or ""),
        author=str(body.get("author") or "analyst"),
    )
    return {
        "ok": True,
        "workstream_id": RW_WORKSTREAM_ID,
        "note": note.to_dict(),
        "mutates_system_intelligence": False,
        "system_generated": False,
    }
