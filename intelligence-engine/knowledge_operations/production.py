"""KOC V1.2 production façades — Institutional Knowledge Mission Control."""

from __future__ import annotations

from typing import Any, Dict, Optional

from knowledge_operations.flags import is_koc_enabled
from knowledge_operations.schema import (
    DOCUMENT_UPLOAD_TYPES,
    KOC_PLATFORM,
    KOC_PRODUCT,
    KOC_SPEC,
    KOC_VERSION,
    KOC_WORKSTREAM_ID,
    MISSION,
    ROLE,
    UPLOAD_PIPELINE,
)


def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "enabled": is_koc_enabled(),
        "workstream_id": KOC_WORKSTREAM_ID,
        "product": KOC_PRODUCT,
        "platform": KOC_PLATFORM,
        "version": KOC_VERSION,
        "spec": KOC_SPEC,
        "admin_only": True,
    }


def get_status() -> Dict[str, Any]:
    return {
        **health(),
        "mission": MISSION,
        "role": ROLE,
        "upload_types": list(DOCUMENT_UPLOAD_TYPES),
        "upload_pipeline": list(UPLOAD_PIPELINE),
    }


_OVERVIEW_CACHE: Dict[str, Any] = {}
_OVERVIEW_CACHE_TTL_SEC = 45.0


def get_overview(*, scope: str = "TOP20", deep: bool = False) -> Dict[str, Any]:
    """V1.2 primary payload (alias of desk with explicit name).

    Cached briefly so the admin page can refresh without rebuilding TOP20 rows
    on every click. Pass deep=True for KIL/research-pack enrichment (slow).
    """
    import time

    from knowledge_operations.desk import build_desk

    scope_u = str(scope or "TOP20").upper()
    key = f"{scope_u}:{'deep' if deep else 'light'}"
    hit = _OVERVIEW_CACHE.get(key)
    if isinstance(hit, dict) and (time.time() - float(hit.get("_ts") or 0)) < _OVERVIEW_CACHE_TTL_SEC:
        payload = dict(hit.get("payload") or {})
        payload["cache"] = "hit"
        return payload

    desk = build_desk(scope=scope_u, deep=bool(deep))
    payload = {**desk, "endpoint": "overview", "cache": "miss"}
    _OVERVIEW_CACHE[key] = {"_ts": time.time(), "payload": payload}
    return payload


def get_desk(*, scope: str = "TOP20", deep: bool = False) -> Dict[str, Any]:
    return get_overview(scope=scope, deep=deep)


def get_system_health() -> Dict[str, Any]:
    from knowledge_operations.system_health import build_system_health

    return build_system_health()


def get_coverage(*, scope: str = "TOP20") -> Dict[str, Any]:
    desk = get_overview(scope=scope)
    return {
        "ok": True,
        "scope": scope,
        "table": desk.get("coverage_table"),
        "heatmap": desk.get("coverage_heatmap"),
        "kpis": {
            "icc": (desk.get("kpis") or {}).get("institutional_coverage_complete"),
            "claim_safe": (desk.get("kpis") or {}).get("claim_safe"),
            "research_ready": (desk.get("kpis") or {}).get("research_ready"),
            "knowledge_ready": (desk.get("kpis") or {}).get("knowledge_ready"),
            "knowledge_confidence": (desk.get("kpis") or {}).get("knowledge_confidence"),
        },
    }


def get_missing_inbox(*, scope: str = "TOP20", limit: int = 50) -> Dict[str, Any]:
    from knowledge_operations.missing_inbox import build_missing_inbox

    return build_missing_inbox(scope=scope, limit=limit)


def get_missing_knowledge(*, scope: str = "TOP20", limit: int = 50) -> Dict[str, Any]:
    return get_missing_inbox(scope=scope, limit=limit)


def get_company(ticker: str) -> Dict[str, Any]:
    from knowledge_operations.desk import company_detail

    return company_detail(ticker)


def get_collectors() -> Dict[str, Any]:
    desk = get_overview(scope="TOP20")
    return {
        "ok": True,
        "collectors": desk.get("collector_health"),
        "success_pct": (desk.get("kpis") or {}).get("collector_success_pct"),
    }


def get_evidence(**kwargs: Any) -> Dict[str, Any]:
    from knowledge_operations.evidence_explorer import search_evidence

    return search_evidence(**kwargs)


def get_evidence_detail(ticker: str, document_id: str) -> Dict[str, Any]:
    from knowledge_operations.evidence_explorer import evidence_detail

    return evidence_detail(ticker, document_id)


def get_knowledge_versions(*, limit: int = 20) -> Dict[str, Any]:
    try:
        from institutional_evidence.integration.versioning.snapshots import list_snapshots

        return list_snapshots(limit=limit)
    except Exception:
        desk = get_overview(scope="TOP20")
        return {"ok": True, "snapshots": desk.get("knowledge_versions") or []}


def get_gap_ai(*, scope: str = "TOP20", limit: int = 30) -> Dict[str, Any]:
    from knowledge_operations.gap_ai import analyze_gaps

    return analyze_gaps(scope=scope, limit=limit)


def find_missing_knowledge(ticker: str) -> Dict[str, Any]:
    from knowledge_operations.gap_ai import find_missing_knowledge as _find

    return _find(ticker)


def global_search(q: str, *, limit: int = 30) -> Dict[str, Any]:
    from knowledge_operations.evidence_explorer import global_search as _gs

    return _gs(q, limit=limit)


def upload_knowledge(**kwargs: Any) -> Dict[str, Any]:
    from knowledge_operations.upload import upload_knowledge as _up

    return _up(**kwargs)


def get_queue(*, limit: int = 100) -> Dict[str, Any]:
    from knowledge_operations.upload import list_queue

    return list_queue(limit=limit)


def get_audit(*, limit: int = 100, ticker: Optional[str] = None) -> Dict[str, Any]:
    from knowledge_operations.audit import list_audit

    return list_audit(limit=limit, ticker=ticker)


def run_action(action: str, **kwargs: Any) -> Dict[str, Any]:
    from knowledge_operations.actions import run_action as _run

    return _run(action, **kwargs)


def run_cgl(**kwargs: Any) -> Dict[str, Any]:
    return run_action("run_cgl", **kwargs)


def run_kil(**kwargs: Any) -> Dict[str, Any]:
    return run_action("run_kil", **kwargs)


def run_coverage(**kwargs: Any) -> Dict[str, Any]:
    return run_action("run_full_coverage", **kwargs)


def run_repair(**kwargs: Any) -> Dict[str, Any]:
    return run_action("run_auto_repair", **kwargs)


def soft_slice_mission_control() -> Dict[str, Any]:
    try:
        health_bar = get_system_health()
        inbox = get_missing_inbox(scope="TOP20", limit=5)
        return {
            "status": "ok",
            "board": "Knowledge Operations Center",
            "workstream_id": KOC_WORKSTREAM_ID,
            "version": KOC_VERSION,
            "platform": KOC_PLATFORM,
            "mission": MISSION,
            "missing_inbox_count": inbox.get("count"),
            "critical_gaps": (inbox.get("by_priority") or {}).get("Critical"),
            "system_health": (health_bar.get("bar") or {}),
            "note": "Open /admin/knowledge-operations — admin only",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:240]}
