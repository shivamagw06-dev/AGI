"""Process-local watchlist store + metrics."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional


_LOCK = Lock()
_WATCHLISTS: dict[str, dict[str, Any]] = {}
_RECENT_EVENTS: list[dict[str, Any]] = []
_METRICS: dict[str, Any] = {
    "watchlists": 0,
    "total_entries": 0,
    "adds": 0,
    "removes": 0,
    "events_applied": 0,
}
_RECENT_LIMIT = 100


def put_watchlist(wl: dict[str, Any]) -> dict[str, Any]:
    wid = str(wl.get("watchlist_id") or (wl.get("metadata") or {}).get("watchlist_id") or "").strip()
    if not wid:
        raise ValueError("watchlist_id required")
    with _LOCK:
        _WATCHLISTS[wid] = deepcopy(wl)
        _refresh_metrics_locked()
    return get_watchlist(wid)  # type: ignore[return-value]


def get_watchlist(watchlist_id: str) -> Optional[dict[str, Any]]:
    with _LOCK:
        w = _WATCHLISTS.get(str(watchlist_id).strip())
        return deepcopy(w) if w else None


def list_watchlists() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(w) for w in _WATCHLISTS.values()]


def resolve_watchlist(name_or_id: str) -> Optional[dict[str, Any]]:
    key = str(name_or_id or "").strip()
    if not key:
        return None
    with _LOCK:
        if key in _WATCHLISTS:
            return deepcopy(_WATCHLISTS[key])
        key_l = key.lower()
        for wid, w in _WATCHLISTS.items():
            if wid.lower() == key_l:
                return deepcopy(w)
            meta = w.get("metadata") or {}
            if str(meta.get("name") or "").lower() == key_l:
                return deepcopy(w)
    return None


def record_add() -> None:
    with _LOCK:
        _METRICS["adds"] = int(_METRICS["adds"]) + 1
        _refresh_metrics_locked()


def record_remove() -> None:
    with _LOCK:
        _METRICS["removes"] = int(_METRICS["removes"]) + 1
        _refresh_metrics_locked()


def record_event_applied(summary: dict[str, Any]) -> None:
    with _LOCK:
        _METRICS["events_applied"] = int(_METRICS["events_applied"]) + 1
        _RECENT_EVENTS.append(deepcopy(summary))
        if len(_RECENT_EVENTS) > _RECENT_LIMIT:
            del _RECENT_EVENTS[: len(_RECENT_EVENTS) - _RECENT_LIMIT]


def recent_events(limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_RECENT_EVENTS)
    return rows[-max(0, int(limit)) :]


def _refresh_metrics_locked() -> None:
    _METRICS["watchlists"] = len(_WATCHLISTS)
    _METRICS["total_entries"] = sum(len(w.get("entries") or []) for w in _WATCHLISTS.values())


def metrics() -> dict[str, Any]:
    with _LOCK:
        m = deepcopy(_METRICS)
    return {
        **m,
        "panels": {
            "watchlists": m.get("watchlists"),
            "total_entries": m.get("total_entries"),
            "adds": m.get("adds"),
            "removes": m.get("removes"),
            "events_applied": m.get("events_applied"),
        },
    }


def reset_for_tests() -> None:
    with _LOCK:
        _WATCHLISTS.clear()
        _RECENT_EVENTS.clear()
        _METRICS["watchlists"] = 0
        _METRICS["total_entries"] = 0
        _METRICS["adds"] = 0
        _METRICS["removes"] = 0
        _METRICS["events_applied"] = 0
