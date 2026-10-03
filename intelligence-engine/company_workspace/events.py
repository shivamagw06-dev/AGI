"""PEB-01 subscriptions — refresh workspace views; never analyse."""

from __future__ import annotations

from threading import Lock
from typing import Any

from company_workspace import store as cw_store

_LOCK = Lock()
_WIRED = False
SUBSCRIBER_ID = "cw-01-workspace-refresh"


def _ticker_from(payload: dict[str, Any]) -> str:
    for key in ("ticker", "symbol", "company"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip().upper()
    tickers = payload.get("tickers")
    if isinstance(tickers, list) and tickers:
        return str(tickers[0]).strip().upper()
    return ""


def _handler(event: dict[str, Any]) -> None:
    """Mark workspace stale and record timeline — no FIRE / no scoring."""
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    et = str(event.get("event_type") or "")
    producer = str(event.get("producer") or "peb")
    ticker = _ticker_from(payload or {})
    if not ticker:
        return

    # Capture research references from IO completions (presentation cache only)
    if et == "company.research.completed":
        cw_store.record_research(
            ticker,
            {
                "package_type": payload.get("package_type"),
                "modules_invoked": payload.get("modules_invoked"),
                "assembly_ms": payload.get("assembly_ms"),
                "status": "completed",
                "source": producer,
                "event_type": et,
            },
        )
        if isinstance(payload.get("module_payloads"), dict):
            cw_store.put_module_cache(ticker, payload["module_payloads"])
        elif isinstance(payload.get("modules"), dict):
            cw_store.put_module_cache(ticker, payload["modules"])

    # Soft-cache quality / execution boards when event carries payload boards
    if et == "business_quality.updated" and isinstance(payload.get("quality"), dict):
        cw_store.put_module_cache(ticker, {"FIRE-06": payload["quality"]})
    if et == "management_execution.updated" and isinstance(payload.get("execution"), dict):
        cw_store.put_module_cache(ticker, {"FIRE-05": payload["execution"]})

    cw_store.append_timeline(
        ticker,
        {
            "at": event.get("ts") or event.get("created_at"),
            "event_type": et,
            "source": producer,
            "summary": f"{et} received — workspace refresh",
            "payload": {
                k: payload.get(k)
                for k in ("package_type", "watchlist_id", "portfolio_id", "priority", "status")
                if k in (payload or {})
            },
        },
    )
    cw_store.mark_refresh(ticker, reason=et or "event")


def ensure_subscriptions() -> dict[str, Any]:
    """Idempotently subscribe CW-01 to office lifecycle events."""
    global _WIRED
    with _LOCK:
        if _WIRED:
            return {"ok": True, "already_wired": True, "subscriber_id": SUBSCRIBER_ID}
        try:
            from platform_event_bus.subscriber import subscribe
            from platform_event_bus.schema import (
                EVENT_BUSINESS_QUALITY_UPDATED,
                EVENT_COMPANY_RESEARCH_COMPLETED,
                EVENT_MANAGEMENT_EXECUTION_UPDATED,
                EVENT_PORTFOLIO_SNAPSHOT_CREATED,
                EVENT_PORTFOLIO_UPDATED,
                EVENT_WATCHLIST_COMPANY_ADDED,
                EVENT_WATCHLIST_COMPANY_REMOVED,
            )

            patterns = [
                EVENT_COMPANY_RESEARCH_COMPLETED,
                EVENT_BUSINESS_QUALITY_UPDATED,
                EVENT_MANAGEMENT_EXECUTION_UPDATED,
                EVENT_WATCHLIST_COMPANY_ADDED,
                EVENT_WATCHLIST_COMPANY_REMOVED,
                "watchlist.*",
                EVENT_PORTFOLIO_UPDATED,
                EVENT_PORTFOLIO_SNAPSHOT_CREATED,
                "portfolio.*",
            ]
            sid = subscribe(
                patterns,
                _handler,
                subscriber_id=SUBSCRIBER_ID,
                name="CW-01 Workspace Refresh",
            )
            _WIRED = True
            return {"ok": True, "already_wired": False, "subscriber_id": sid, "patterns": patterns}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def reset_subscriptions_for_tests() -> None:
    global _WIRED
    with _LOCK:
        _WIRED = False
        try:
            from platform_event_bus.dispatcher import get_dispatcher

            get_dispatcher().unsubscribe(SUBSCRIBER_ID)
        except Exception:
            pass
