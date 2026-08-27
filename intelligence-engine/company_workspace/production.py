"""CW-01 production façades — Company Workspace UX assembly (read-only)."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from company_workspace.assemble import assemble_workspace
from company_workspace.events import ensure_subscriptions
from company_workspace.flags import flags_dict, is_enabled
from company_workspace.schema import (
    CW01_DOMAIN,
    CW01_PRODUCT,
    CW01_RECOMMENDATION_POLICY,
    CW01_SPEC,
    CW01_SUBSYSTEM,
    CW01_SURFACE_ID,
    CW01_VERSION,
    CW01_WORKSTREAM_ID,
    WORKSPACE_SECTIONS,
)
from company_workspace.search import filter_timeline, search_workspace
from company_workspace import store as cw_store

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    ensure_subscriptions()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": CW01_WORKSTREAM_ID,
        "surface_id": CW01_SURFACE_ID,
        "product": CW01_PRODUCT,
        "subsystem": CW01_SUBSYSTEM,
        "version": CW01_VERSION,
        "domain": CW01_DOMAIN,
        "role": "company_user_experience",
        "not_an_engine": True,
        "not_an_office": True,
        "presentation_only": True,
        "runs_fire": False,
        "buy_sell": False,
        "valuation": False,
        "forecast": False,
        "recommendation_policy": CW01_RECOMMENDATION_POLICY,
        "sections": list(WORKSPACE_SECTIONS),
        "consumes": [
            "IO-01",
            "CIO-01",
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FIRE-04",
            "FIRE-05",
            "FIRE-06",
            "Office SDK",
            "PEB-01",
            "WO-01",
            "PO-01",
        ],
        "subscribes": [
            "company.research.completed",
            "business_quality.updated",
            "management_execution.updated",
            "watchlist.*",
            "portfolio.*",
        ],
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": CW01_SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    ensure_subscriptions()
    m = cw_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": CW01_WORKSTREAM_ID,
        "version": CW01_VERSION,
        "buy_sell": False,
        "presentation_only": True,
        "panels": m.get("panels") or {},
        "metrics": m,
        "spec": CW01_SPEC,
        "as_of": now_iso(),
    }


def workspace(
    ticker: str,
    *,
    profile: Optional[Mapping[str, Any]] = None,
    prebuilt: Optional[Mapping[str, Mapping[str, Any]]] = None,
    question: Optional[str] = None,
    sections: Optional[Sequence[str]] = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    ensure_subscriptions()
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": CW01_WORKSTREAM_ID,
            "surface_id": CW01_SURFACE_ID,
        }
    resp = assemble_workspace(
        ticker,
        profile=profile,
        prebuilt=prebuilt,
        question=question,
        section_filter=sections,
        use_cache=use_cache,
    )
    return {
        "ok": bool(resp.get("ok")),
        "enabled": True,
        "workstream_id": CW01_WORKSTREAM_ID,
        "surface_id": CW01_SURFACE_ID,
        "version": CW01_VERSION,
        "presentation_only": True,
        "buy_sell": False,
        "runs_fire": False,
        "office_response": resp,
        "ticker": str(ticker or "").strip().upper(),
        "payload": resp.get("payload"),
        "sections": resp.get("sections"),
        "confidence": resp.get("confidence"),
        "provenance": resp.get("provenance"),
    }


def timeline(
    ticker: str,
    *,
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
) -> dict[str, Any]:
    ensure_subscriptions()
    t = str(ticker or "").strip().upper()
    events = cw_store.list_timeline(t, limit=limit)
    filtered = filter_timeline(events, event_type=event_type, source=source, query=query)
    return {
        "ok": True,
        "workstream_id": CW01_WORKSTREAM_ID,
        "ticker": t,
        "events": filtered,
        "count": len(filtered),
        "presentation_only": True,
    }


def research(ticker: str) -> dict[str, Any]:
    ensure_subscriptions()
    t = str(ticker or "").strip().upper()
    history = cw_store.list_research(t)
    return {
        "ok": True,
        "workstream_id": CW01_WORKSTREAM_ID,
        "ticker": t,
        "latest": history[-1] if history else None,
        "history": history,
        "count": len(history),
        "presentation_only": True,
    }


def evidence(ticker: str, *, query: Optional[str] = None) -> dict[str, Any]:
    ensure_subscriptions()
    pack = workspace(ticker, use_cache=True)
    resp = pack.get("office_response") or {}
    if query:
        found = search_workspace(resp, query, scope="evidence")
        return {
            "ok": True,
            "workstream_id": CW01_WORKSTREAM_ID,
            "ticker": str(ticker or "").strip().upper(),
            "query": query,
            "evidence": found.get("evidence") or [],
            "count": len(found.get("evidence") or []),
            "presentation_only": True,
        }
    prov = resp.get("provenance") or {}
    references = list(prov.get("references") or [])
    blocks = list(prov.get("blocks") or [])
    return {
        "ok": True,
        "workstream_id": CW01_WORKSTREAM_ID,
        "ticker": str(ticker or "").strip().upper(),
        "references": references,
        "blocks": blocks,
        "count": len(references),
        "presentation_only": True,
    }


def search(
    ticker: str,
    query: str,
    *,
    scope: str = "all",
) -> dict[str, Any]:
    ensure_subscriptions()
    pack = workspace(ticker, use_cache=True)
    resp = pack.get("office_response") or {}
    return {
        "ok": True,
        "workstream_id": CW01_WORKSTREAM_ID,
        "ticker": str(ticker or "").strip().upper(),
        **search_workspace(resp, query, scope=scope),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    ensure_subscriptions()
    m = cw_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": CW01_WORKSTREAM_ID,
        "surface_id": CW01_SURFACE_ID,
        "product": CW01_PRODUCT,
        "version": CW01_VERSION,
        "buy_sell": False,
        "presentation_only": True,
        "panels": {
            "companies_viewed": (m.get("panels") or {}).get("companies_viewed"),
            "workspace_refreshes": (m.get("panels") or {}).get("workspace_refreshes"),
            "coverage": (m.get("panels") or {}).get("coverage"),
            "evidence_completeness": (m.get("panels") or {}).get("evidence_completeness"),
        },
        "metrics": m,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>CW-01 Company Workspace</title></head>
<body>
<h1>CW-01 — Company Workspace</h1>
<pre>{h}</pre>
<p>Primary company UX. Assembles existing intelligence. No FIRE runs. No BUY/SELL.</p>
</body></html>"""
