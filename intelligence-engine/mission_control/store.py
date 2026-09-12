"""Process-local Mission Control cache + acknowledged alerts."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from time import monotonic
from typing import Any


_LOCK = Lock()
_DASH: dict[str, Any] | None = None
_DASH_AT: float = 0.0
_ACK: set[str] = set()

# Short TTL keeps the cockpit snappy under parallel health/dashboard/gates calls.
# Stale window lets cold Render boots serve the last good desk instead of hanging.
_DASH_TTL_SEC = 120.0
_DASH_STALE_SEC = 900.0


def put_dashboard(row: dict[str, Any]) -> dict[str, Any]:
    global _DASH, _DASH_AT
    with _LOCK:
        _DASH = deepcopy(row)
        _DASH_AT = monotonic()
    return row


def get_dashboard(*, max_age_sec: float | None = None, allow_stale: bool = False) -> dict[str, Any] | None:
    ttl = _DASH_TTL_SEC if max_age_sec is None else max_age_sec
    with _LOCK:
        if not _DASH:
            return None
        age = monotonic() - _DASH_AT
        if ttl >= 0 and age > ttl:
            if allow_stale and age <= _DASH_STALE_SEC:
                out = deepcopy(_DASH)
                out["_cache"] = {"stale": True, "age_sec": round(age, 1)}
                return out
            return None
        out = deepcopy(_DASH)
        out["_cache"] = {"stale": False, "age_sec": round(age, 1)}
        return out

def acknowledge(alert_id: str, *, actor: str | None = None) -> dict[str, Any]:
    aid = str(alert_id or "").strip()
    with _LOCK:
        if aid:
            _ACK.add(aid)
        return {
            "ok": True,
            "acknowledged": True,
            "alert_id": aid,
            "actor": actor,
            "acknowledged_ids": sorted(_ACK),
        }


def acknowledged_ids() -> set[str]:
    with _LOCK:
        return set(_ACK)


def reset_for_tests() -> None:
    global _DASH, _DASH_AT
    with _LOCK:
        _DASH = None
        _DASH_AT = 0.0
        _ACK.clear()
