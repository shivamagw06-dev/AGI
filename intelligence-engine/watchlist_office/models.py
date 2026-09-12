"""Watchlist / research-queue entry models — state only; no research."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from watchlist_office.schema import ENTRY_PRIORITIES, ENTRY_STATUSES


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (name or "").strip()).strip("-").lower()
    return s or "watchlist"


def watchlist_metadata(
    *,
    watchlist_id: Optional[str] = None,
    name: str,
    owner: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "active",
) -> dict[str, Any]:
    wid = (watchlist_id or _slug(name)).strip()
    return {
        "schema": "wo01.watchlist_metadata.v1",
        "watchlist_id": wid,
        "name": name.strip() or wid,
        "owner": owner,
        "description": description,
        "status": status,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def watchlist_entry(
    *,
    ticker: str,
    company: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
    priority: str = "Medium",
    status: str = "New",
    notes: Optional[str] = None,
    extras: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    t = str(ticker or "").strip().upper()
    pri = priority if priority in ENTRY_PRIORITIES else "Medium"
    st = status if status in ENTRY_STATUSES else "New"
    row: dict[str, Any] = {
        "schema": "wo01.watchlist_entry.v1",
        "ticker": t,
        "company": company or t,
        "tags": [str(x) for x in (tags or []) if str(x).strip()],
        "priority": pri,
        "status": st,
        "notes": notes,
        "added_at": _now_iso(),
        "updated_at": _now_iso(),
        # Intelligence references (timestamps / snapshots only — never recalculated here)
        "last_research_at": None,
        "last_comparison_at": None,
        "last_business_quality_at": None,
        "last_business_quality_score": None,
        "last_execution_at": None,
        "last_execution_summary": None,
        "last_event_type": None,
        "last_event_at": None,
        "last_event_id": None,
        "last_event_payload": None,
        "research_refs": [],  # soft pointers to IO/FIRE outputs
    }
    if extras:
        row["extras"] = dict(extras)
    return row


def watchlist(
    *,
    metadata: Mapping[str, Any],
    entries: Optional[Sequence[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    meta = dict(metadata)
    return {
        "schema": "wo01.watchlist.v1",
        "watchlist_id": meta.get("watchlist_id"),
        "metadata": meta,
        "entries": [deepcopy(dict(e)) for e in (entries or [])],
        "updated_at": _now_iso(),
        "role": "research_queue",
        "performs_research": False,
        "buy_sell": False,
    }
