"""Living listed-universe tracker — coverage is never permanently "finished".

Tracks current listed set, new listings / IPOs, delists, and pending IPOs.
New listings are auto-enqueued for historical backfill from listing date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.universe_priority import supported_universe

UNIVERSE_SNAPSHOT = "living_listed_universe"
PENDING_IPOS = "pending_ipos_registry"
UNIVERSE_EVENTS = "living_universe_events"
VERSION = "living-universe-v1.0.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_snapshot() -> dict[str, Any]:
    return hd_store.get_report(UNIVERSE_SNAPSHOT) or {
        "listed": [],
        "delisted": [],
        "updated_at": None,
        "version": VERSION,
    }


def load_pending_ipos() -> list[dict[str, Any]]:
    raw = hd_store.get_report(PENDING_IPOS) or {}
    return list(raw.get("ipos") or [])


def save_pending_ipos(ipos: list[dict[str, Any]]) -> dict[str, Any]:
    body = {"ipos": ipos, "updated_at": _now(), "version": VERSION, "n": len(ipos)}
    hd_store.put_report(PENDING_IPOS, body)
    return body


def register_pending_ipo(
    *,
    symbol: str,
    name: str | None = None,
    expected_listing: str | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    """Register a pending IPO so Mission Control can surface it before listing."""
    sym = symbol.upper().strip()
    ipos = load_pending_ipos()
    existing = {str(i.get("symbol") or "").upper(): i for i in ipos}
    existing[sym] = {
        "symbol": sym,
        "name": name or sym,
        "expected_listing": expected_listing,
        "status": "pending",
        "source": source,
        "registered_at": (existing.get(sym) or {}).get("registered_at") or _now(),
        "updated_at": _now(),
    }
    save_pending_ipos(list(existing.values()))
    return existing[sym]


def _append_event(kind: str, payload: dict[str, Any]) -> None:
    raw = hd_store.get_report(UNIVERSE_EVENTS) or {"events": []}
    events = list(raw.get("events") or [])
    events.insert(0, {"kind": kind, "at": _now(), **payload})
    hd_store.put_report(UNIVERSE_EVENTS, {"events": events[:500], "updated_at": _now()})


def sync_listed_universe(*, extra_listed: list[str] | None = None) -> dict[str, Any]:
    """Diff current supported universe vs last snapshot; enqueue new listings.

    Returns living-universe board metrics. Never marks coverage as permanently finished.
    """
    prev = load_snapshot()
    prev_listed = {str(x).upper() for x in (prev.get("listed") or [])}
    prev_delisted = {str(x).upper() for x in (prev.get("delisted") or [])}

    current = {str(x).upper() for x in supported_universe()}
    if extra_listed:
        current |= {str(x).upper() for x in extra_listed}

    # Promote pending IPOs that now appear in the listed set
    pending = load_pending_ipos()
    still_pending: list[dict[str, Any]] = []
    newly_listed_from_ipo: list[str] = []
    for ipo in pending:
        sym = str(ipo.get("symbol") or "").upper()
        if not sym:
            continue
        if sym in current:
            newly_listed_from_ipo.append(sym)
            _append_event("ipo_listed", {"symbol": sym, "name": ipo.get("name")})
        else:
            still_pending.append(ipo)
    if newly_listed_from_ipo:
        save_pending_ipos(still_pending)

    new_listings = sorted((current - prev_listed) | set(newly_listed_from_ipo))
    # First bootstrap: don't treat entire universe as "new"
    if not prev_listed:
        new_listings = []

    delisted = sorted(prev_listed - current)
    # Keep historical delist registry
    delisted_all = sorted(prev_delisted | set(delisted))

    enqueued: list[str] = []
    if new_listings:
        from knowledge_factory.historical_depth import queue as bf_queue

        for sym in new_listings:
            bf_queue.enqueue_company(
                sym,
                reason="new_listing" if sym not in newly_listed_from_ipo else "ipo_listed",
                listing_date=_infer_listing_date(sym),
            )
            enqueued.append(sym)
            _append_event("new_listing_enqueued", {"symbol": sym})

    for sym in delisted:
        _append_event("delisted", {"symbol": sym})
        # Mark queue row delisted (soft — keep history)
        try:
            from knowledge_factory.historical_depth import queue as bf_queue

            bf_queue.mark_delisted(sym)
        except Exception:
            pass

    snap = {
        "version": VERSION,
        "listed": sorted(current),
        "delisted": delisted_all,
        "new_listings_this_sync": new_listings,
        "delisted_this_sync": delisted,
        "enqueued": enqueued,
        "pending_ipos": len(still_pending),
        "current_listed_universe": len(current),
        "updated_at": _now(),
        "note": "Coverage is never permanently finished — universe changes over time",
    }
    hd_store.put_report(UNIVERSE_SNAPSHOT, snap)

    covered = _covered_count(current)
    return {
        "current_listed_universe": len(current),
        "covered_companies": covered,
        "coverage_pct": round(100.0 * covered / max(1, len(current)), 2),
        "new_listings": new_listings,
        "new_listings_count": len(new_listings),
        "delisted_companies": delisted,
        "delisted_count": len(delisted),
        "delisted_total": len(delisted_all),
        "pending_ipos": still_pending,
        "pending_ipos_count": len(still_pending),
        "enqueued": enqueued,
        "queue_ready": True,
        "coverage_finished": False,
        "updated_at": snap["updated_at"],
    }


def _covered_count(listed: set[str]) -> int:
    try:
        from knowledge_factory.historical_depth import queue as bf_queue

        q = bf_queue.load_queue()
        by = {str(c.get("company") or "").upper(): c for c in (q.get("companies") or [])}
        n = 0
        for sym in listed:
            row = by.get(sym)
            if row and str(row.get("status")) in {bf_queue.STATUS_MAINTENANCE, bf_queue.STATUS_COMPLETE}:
                n += 1
        return n
    except Exception:
        return 0


def _infer_listing_date(symbol: str) -> str | None:
    try:
        series = hd_store.get_series("prices", symbol) or {}
        ends = [str(r.get("period_end") or "")[:10] for r in (series.get("records") or []) if r.get("period_end")]
        return min(ends) if ends else None
    except Exception:
        return None


def living_universe_board() -> dict[str, Any]:
    """Mission Control board — living coverage, never 'finished'."""
    # Soft sync each read keeps queue ready for new work
    try:
        sync = sync_listed_universe()
    except Exception as exc:  # noqa: BLE001
        snap = load_snapshot()
        sync = {
            "current_listed_universe": len(snap.get("listed") or []),
            "covered_companies": 0,
            "coverage_pct": 0.0,
            "new_listings": [],
            "new_listings_count": 0,
            "delisted_companies": [],
            "delisted_count": 0,
            "pending_ipos": load_pending_ipos(),
            "pending_ipos_count": len(load_pending_ipos()),
            "error": str(exc)[:160],
            "coverage_finished": False,
            "queue_ready": True,
        }
    events = (hd_store.get_report(UNIVERSE_EVENTS) or {}).get("events") or []
    return {
        **sync,
        "recent_events": events[:20],
        "version": VERSION,
        "north_star": "Track living listed universe — backlog usually empty, always ready for new listings/IPOs",
    }
