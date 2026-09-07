"""Watchlist research-queue service — add/remove/update; never researches."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from watchlist_office.models import watchlist, watchlist_entry, watchlist_metadata
from watchlist_office.schema import ENTRY_PRIORITIES, ENTRY_STATUSES
from watchlist_office import store as wl_store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_watchlist(
    *,
    name: str,
    owner: Optional[str] = None,
    description: Optional[str] = None,
    watchlist_id: Optional[str] = None,
    entries: Optional[Sequence[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    meta = watchlist_metadata(
        watchlist_id=watchlist_id,
        name=name,
        owner=owner,
        description=description,
    )
    built = []
    for e in entries or []:
        built.append(
            watchlist_entry(
                ticker=str(e.get("ticker") or ""),
                company=e.get("company"),
                tags=e.get("tags"),
                priority=str(e.get("priority") or "Medium"),
                status=str(e.get("status") or "New"),
                notes=e.get("notes"),
            )
        )
    wl = watchlist(metadata=meta, entries=built)
    return wl_store.put_watchlist(wl)


def add_company(
    watchlist_id: str,
    ticker: str,
    *,
    company: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
    priority: str = "Medium",
    status: str = "New",
    notes: Optional[str] = None,
) -> dict[str, Any]:
    wl = wl_store.resolve_watchlist(watchlist_id)
    if not wl:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    t = str(ticker or "").strip().upper()
    if not t:
        raise ValueError("ticker required")
    entries = list(wl.get("entries") or [])
    if any(str(e.get("ticker") or "").upper() == t for e in entries):
        # Idempotent add — return existing
        return {"watchlist": wl, "entry": next(e for e in entries if e.get("ticker") == t), "created": False}

    entry = watchlist_entry(
        ticker=t,
        company=company,
        tags=tags,
        priority=priority,
        status=status,
        notes=notes,
    )
    entries.append(entry)
    wl["entries"] = entries
    wl["updated_at"] = _now_iso()
    meta = dict(wl.get("metadata") or {})
    meta["updated_at"] = _now_iso()
    wl["metadata"] = meta
    wl = wl_store.put_watchlist(wl)
    wl_store.record_add()

    # PEB publish
    try:
        from platform_event_bus.publisher import soft_publish
        from platform_event_bus.schema import EVENT_WATCHLIST_COMPANY_ADDED

        soft_publish(
            EVENT_WATCHLIST_COMPANY_ADDED,
            producer="wo-01",
            payload={
                "watchlist_id": wl.get("watchlist_id"),
                "ticker": t,
                "priority": entry.get("priority"),
                "status": entry.get("status"),
                "tags": entry.get("tags"),
            },
        )
    except Exception:
        pass

    return {"watchlist": wl, "entry": entry, "created": True}


def remove_company(watchlist_id: str, ticker: str) -> dict[str, Any]:
    wl = wl_store.resolve_watchlist(watchlist_id)
    if not wl:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    t = str(ticker or "").strip().upper()
    before = list(wl.get("entries") or [])
    after = [e for e in before if str(e.get("ticker") or "").upper() != t]
    if len(after) == len(before):
        return {"watchlist": wl, "removed": False, "ticker": t}
    wl["entries"] = after
    wl["updated_at"] = _now_iso()
    wl = wl_store.put_watchlist(wl)
    wl_store.record_remove()
    try:
        from platform_event_bus.publisher import soft_publish
        from platform_event_bus.schema import EVENT_WATCHLIST_COMPANY_REMOVED

        soft_publish(
            EVENT_WATCHLIST_COMPANY_REMOVED,
            producer="wo-01",
            payload={"watchlist_id": wl.get("watchlist_id"), "ticker": t},
        )
    except Exception:
        pass
    return {"watchlist": wl, "removed": True, "ticker": t}


def update_entry(
    watchlist_id: str,
    ticker: str,
    *,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    wl = wl_store.resolve_watchlist(watchlist_id)
    if not wl:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    t = str(ticker or "").strip().upper()
    entries = list(wl.get("entries") or [])
    found = None
    for e in entries:
        if str(e.get("ticker") or "").upper() == t:
            if priority and priority in ENTRY_PRIORITIES:
                e["priority"] = priority
            if status and status in ENTRY_STATUSES:
                e["status"] = status
            if notes is not None:
                e["notes"] = notes
            if tags is not None:
                e["tags"] = [str(x) for x in tags if str(x).strip()]
            e["updated_at"] = _now_iso()
            found = e
            break
    if not found:
        raise ValueError(f"ticker not on watchlist: {t}")
    wl["entries"] = entries
    wl["updated_at"] = _now_iso()
    wl = wl_store.put_watchlist(wl)
    return {"watchlist": wl, "entry": found}


def research_queue(watchlist_id: str) -> dict[str, Any]:
    """Ordered research queue: active statuses first, then by priority."""
    wl = wl_store.resolve_watchlist(watchlist_id)
    if not wl:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    pri_rank = {p: i for i, p in enumerate(ENTRY_PRIORITIES)}
    st_rank = {"New": 0, "Reviewing": 1, "Monitoring": 2, "Archived": 3}
    entries = list(wl.get("entries") or [])
    active = [e for e in entries if e.get("status") != "Archived"]
    archived = [e for e in entries if e.get("status") == "Archived"]
    active.sort(
        key=lambda e: (
            st_rank.get(str(e.get("status")), 9),
            pri_rank.get(str(e.get("priority")), 9),
            str(e.get("ticker") or ""),
        )
    )
    return {
        "watchlist_id": wl.get("watchlist_id"),
        "queue": active,
        "archived": archived,
        "counts": {
            "active": len(active),
            "archived": len(archived),
            "by_status": _count_by(entries, "status"),
            "by_priority": _count_by(active, "priority"),
        },
    }


def _count_by(entries: list[dict[str, Any]], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in entries:
        k = str(e.get(field) or "Unknown")
        out[k] = out.get(k, 0) + 1
    return out


def apply_event_to_entries(event: Mapping[str, Any]) -> int:
    """
    Soft-apply PEB events onto matching watchlist entries.
    Never runs research — only updates reference timestamps / snapshot fields.
    """
    et = str(event.get("event_type") or "")
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    tickers: list[str] = []
    if payload.get("ticker"):
        tickers.append(str(payload["ticker"]).upper())
    for t in payload.get("tickers") or []:
        tickers.append(str(t).upper())
    tickers = list(dict.fromkeys([t for t in tickers if t]))
    if not tickers:
        return 0

    updated = 0
    now = str(event.get("timestamp") or _now_iso())
    for wl in wl_store.list_watchlists():
        changed = False
        entries = list(wl.get("entries") or [])
        for e in entries:
            if str(e.get("ticker") or "").upper() not in tickers:
                continue
            e["last_event_type"] = et
            e["last_event_at"] = now
            e["last_event_id"] = event.get("event_id")
            e["last_event_payload"] = {
                k: payload.get(k)
                for k in ("ticker", "tickers", "package_type", "comparison_type", "modules_invoked")
                if k in payload
            }
            e["updated_at"] = _now_iso()

            if et == "company.research.completed":
                e["last_research_at"] = now
                refs = list(e.get("research_refs") or [])
                refs.append(
                    {
                        "source": "io-01",
                        "event_id": event.get("event_id"),
                        "at": now,
                        "package_type": payload.get("package_type"),
                    }
                )
                e["research_refs"] = refs[-20:]
                if e.get("status") == "New":
                    e["status"] = "Reviewing"
            elif et == "comparison.completed":
                e["last_comparison_at"] = now
            elif et == "business_quality.updated":
                e["last_business_quality_at"] = now
                if isinstance(payload.get("score"), (int, float)):
                    e["last_business_quality_score"] = float(payload["score"])
                elif isinstance(payload.get("overall_score"), (int, float)):
                    e["last_business_quality_score"] = float(payload["overall_score"])
            elif et == "management_execution.updated":
                e["last_execution_at"] = now
                e["last_execution_summary"] = payload.get("summary") or payload.get("status")

            changed = True
            updated += 1
        if changed:
            wl["entries"] = entries
            wl["updated_at"] = _now_iso()
            wl_store.put_watchlist(wl)

    if updated:
        wl_store.record_event_applied(
            {
                "event_id": event.get("event_id"),
                "event_type": et,
                "tickers": tickers,
                "entries_updated": updated,
                "at": now,
            }
        )
    return updated
