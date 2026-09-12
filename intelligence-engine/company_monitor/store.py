"""Process-local monitor store — snapshots, changes, alerts."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any


_LOCK = Lock()
_SNAPSHOTS: dict[str, dict[str, Any]] = {}  # ticker -> latest snapshot
_PREVIOUS: dict[str, dict[str, Any]] = {}  # ticker -> previous snapshot
_CHANGES: dict[str, list[dict[str, Any]]] = {}  # ticker -> change events
_ALERTS: list[dict[str, Any]] = []
_REVIEWS: dict[str, dict[str, Any]] = {}  # ticker -> suggested house view review


def put_snapshot(ticker: str, snap: dict[str, Any]) -> dict[str, Any]:
    t = (ticker or "").upper()
    with _LOCK:
        prev = _SNAPSHOTS.get(t)
        if prev:
            _PREVIOUS[t] = deepcopy(prev)
        _SNAPSHOTS[t] = deepcopy(snap)
    return snap


def get_snapshot(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").upper()
    with _LOCK:
        row = _SNAPSHOTS.get(t)
        return deepcopy(row) if row else None


def get_previous(ticker: str) -> dict[str, Any] | None:
    t = (ticker or "").upper()
    with _LOCK:
        row = _PREVIOUS.get(t)
        return deepcopy(row) if row else None


def add_change(ticker: str, change: dict[str, Any]) -> None:
    t = (ticker or "").upper()
    with _LOCK:
        bucket = _CHANGES.setdefault(t, [])
        bucket.insert(0, deepcopy(change))
        del bucket[80:]
        if str(change.get("significance") or "") in {"High", "Critical"}:
            _ALERTS.insert(0, {"ticker": t, **deepcopy(change)})
            del _ALERTS[100:]


def list_changes(ticker: str | None = None, *, limit: int = 40) -> list[dict[str, Any]]:
    with _LOCK:
        if ticker:
            rows = list(_CHANGES.get(ticker.upper(), []))
        else:
            rows = []
            for t, items in _CHANGES.items():
                for it in items:
                    rows.append({"ticker": t, **it})
            rows.sort(key=lambda r: str(r.get("detected_at") or ""), reverse=True)
    return [deepcopy(x) for x in rows[:limit]]


def list_alerts(limit: int = 40) -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(x) for x in _ALERTS[:limit]]


def put_review(ticker: str, review: dict[str, Any]) -> None:
    with _LOCK:
        _REVIEWS[(ticker or "").upper()] = deepcopy(review)


def list_reviews(limit: int = 40) -> list[dict[str, Any]]:
    with _LOCK:
        items = list(_REVIEWS.values())
    items.sort(key=lambda r: str(r.get("suggested_at") or ""), reverse=True)
    return [deepcopy(x) for x in items[:limit]]


def monitored_tickers() -> list[str]:
    with _LOCK:
        return sorted(_SNAPSHOTS.keys())


def metrics() -> dict[str, Any]:
    with _LOCK:
        n = len(_SNAPSHOTS)
        critical = sum(1 for a in _ALERTS if a.get("significance") == "Critical")
        high = sum(1 for a in _ALERTS if a.get("significance") == "High")
        reviews = len(_REVIEWS)
        change_n = sum(len(v) for v in _CHANGES.values())
    return {
        "companies_monitored": n,
        "change_events": change_n,
        "critical_alerts": critical,
        "high_alerts": high,
        "companies_needing_review": reviews,
    }


def reset_for_tests() -> None:
    with _LOCK:
        _SNAPSHOTS.clear()
        _PREVIOUS.clear()
        _CHANGES.clear()
        _ALERTS.clear()
        _REVIEWS.clear()
