"""In-memory Corporate Event Intelligence store (soft, immutable timelines)."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

_LOCK = RLock()
_EVENTS: dict[str, dict[str, Any]] = {}  # event_id -> event
_TIMELINES: dict[str, dict[str, Any]] = {}  # ticker -> timeline object
_RUNS: list[dict[str, Any]] = []


def reset() -> None:
    with _LOCK:
        _EVENTS.clear()
        _TIMELINES.clear()
        _RUNS.clear()


def put_event(event: dict[str, Any]) -> dict[str, Any]:
    eid = str(event.get("event_id") or "")
    if not eid:
        raise ValueError("event requires event_id")
    with _LOCK:
        # Immutable: do not overwrite an existing event_id with different content
        existing = _EVENTS.get(eid)
        if existing is not None:
            return deepcopy(existing)
        _EVENTS[eid] = deepcopy(event)
        return deepcopy(_EVENTS[eid])


def get_event(event_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _EVENTS.get(str(event_id or ""))
        return deepcopy(row) if row else None


def put_timeline(ticker: str, timeline: dict[str, Any]) -> dict[str, Any]:
    t = str(ticker or "").upper()
    with _LOCK:
        _TIMELINES[t] = deepcopy(timeline)
        return deepcopy(_TIMELINES[t])


def get_timeline(ticker: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _TIMELINES.get(str(ticker or "").upper())
        return deepcopy(row) if row else None


def list_timelines() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_TIMELINES.items())]


def list_events(*, ticker: str | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_EVENTS.values())
        if ticker:
            t = ticker.upper()
            rows = [e for e in rows if str(e.get("company") or "").upper() == t]
        return [deepcopy(e) for e in sorted(rows, key=lambda x: (x.get("announcement_date") or "", x.get("event_id") or ""))]


def event_count() -> int:
    with _LOCK:
        return len(_EVENTS)


def timeline_count() -> int:
    with _LOCK:
        return len(_TIMELINES)


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(summary))
        if len(_RUNS) > 50:
            del _RUNS[:-50]


def last_run() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_RUNS[-1]) if _RUNS else None
