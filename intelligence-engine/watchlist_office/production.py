"""WO-01 production façades — research-queue watchlists."""

from __future__ import annotations

from typing import Any, Optional

from watchlist_office.events import ensure_subscriptions
from watchlist_office.flags import flags_dict, is_enabled
from watchlist_office.report import build_wqr
from watchlist_office.schema import (
    WO01_OFFICE_ID,
    WO01_PRODUCT,
    WO01_RECOMMENDATION_POLICY,
    WO01_SPEC,
    WO01_SUBSYSTEM,
    WO01_VERSION,
    WO01_WORKSTREAM_ID,
)
from watchlist_office.service import (
    add_company,
    create_watchlist,
    remove_company,
    research_queue,
    update_entry,
)
from watchlist_office import store as wl_store

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
        "workstream_id": WO01_WORKSTREAM_ID,
        "office_id": WO01_OFFICE_ID,
        "product": WO01_PRODUCT,
        "subsystem": WO01_SUBSYSTEM,
        "version": WO01_VERSION,
        "domain": "portfolio",
        "role": "research_queue_watchlist",
        "performs_research": False,
        "buy_sell": False,
        "event_driven": True,
        "recommendation_policy": WO01_RECOMMENDATION_POLICY,
        "consumes": ["Office SDK", "PEB-01", "IO-01 references", "FIRE references"],
        "publishes": ["watchlist.company.added", "watchlist.company.removed"],
        "subscribes": [
            "company.research.completed",
            "comparison.completed",
            "business_quality.updated",
            "management_execution.updated",
        ],
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": WO01_SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    ensure_subscriptions()
    m = wl_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": WO01_WORKSTREAM_ID,
        "version": WO01_VERSION,
        "buy_sell": False,
        "panels": m.get("panels") or {},
        "metrics": m,
        "watchlists": [
            {
                "watchlist_id": w.get("watchlist_id"),
                "name": (w.get("metadata") or {}).get("name"),
                "entries_n": len(w.get("entries") or []),
            }
            for w in wl_store.list_watchlists()
        ],
        "spec": WO01_SPEC,
        "as_of": now_iso(),
    }


def get_watchlist(watchlist_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": WO01_WORKSTREAM_ID}
    try:
        wqr = build_wqr(watchlist_id)
        return {
            "ok": True,
            "enabled": True,
            "workstream_id": WO01_WORKSTREAM_ID,
            "office_id": WO01_OFFICE_ID,
            "version": WO01_VERSION,
            "buy_sell": False,
            "office_response": wqr,
            "watchlist": (wqr.get("payload") or {}).get("watchlist"),
            "queue": (wqr.get("payload") or {}).get("queue"),
        }
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "workstream_id": WO01_WORKSTREAM_ID}


def get_queue(watchlist_id: str) -> dict[str, Any]:
    ensure_subscriptions()
    try:
        q = research_queue(watchlist_id)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "workstream_id": WO01_WORKSTREAM_ID, **q}


def create(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_subscriptions()
    if not is_enabled():
        return {"ok": False, "enabled": False}
    name = str(payload.get("name") or payload.get("watchlist_name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    wl = create_watchlist(
        name=name,
        owner=payload.get("owner"),
        description=payload.get("description"),
        watchlist_id=payload.get("watchlist_id"),
        entries=payload.get("entries") or payload.get("companies") or [],
    )
    return {
        "ok": True,
        "workstream_id": WO01_WORKSTREAM_ID,
        "version": WO01_VERSION,
        "watchlist": wl,
        "watchlist_id": wl.get("watchlist_id"),
    }


def add(watchlist_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_subscriptions()
    ticker = str(payload.get("ticker") or payload.get("company_ticker") or "").strip()
    try:
        result = add_company(
            watchlist_id,
            ticker,
            company=payload.get("company"),
            tags=payload.get("tags"),
            priority=str(payload.get("priority") or "Medium"),
            status=str(payload.get("status") or "New"),
            notes=payload.get("notes"),
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "workstream_id": WO01_WORKSTREAM_ID, **result}


def remove(watchlist_id: str, ticker: str) -> dict[str, Any]:
    ensure_subscriptions()
    try:
        result = remove_company(watchlist_id, ticker)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "workstream_id": WO01_WORKSTREAM_ID, **result}


def patch_entry(watchlist_id: str, ticker: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_subscriptions()
    try:
        result = update_entry(
            watchlist_id,
            ticker,
            priority=payload.get("priority"),
            status=payload.get("status"),
            notes=payload.get("notes"),
            tags=payload.get("tags"),
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "workstream_id": WO01_WORKSTREAM_ID, **result}


def soft_slice_mission_control() -> dict[str, Any]:
    ensure_subscriptions()
    m = wl_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": WO01_WORKSTREAM_ID,
        "office_id": WO01_OFFICE_ID,
        "product": WO01_PRODUCT,
        "version": WO01_VERSION,
        "buy_sell": False,
        "event_driven": True,
        "panels": m.get("panels") or {},
        "metrics": m,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>WO-01 Watchlist Office</title></head>
<body>
<h1>WO-01 — Watchlist Office</h1>
<pre>{h}</pre>
<p>Research queue. Event-driven via PEB-01. No BUY/SELL. No research engine.</p>
</body></html>"""
