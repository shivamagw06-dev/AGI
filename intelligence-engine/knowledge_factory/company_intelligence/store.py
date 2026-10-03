"""In-memory Institutional Company Intelligence store (soft, non-authoritative)."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

_LOCK = RLock()
_OBJECTS: dict[str, dict[str, Any]] = {}
_RUNS: list[dict[str, Any]] = []


def reset() -> None:
    with _LOCK:
        _OBJECTS.clear()
        _RUNS.clear()


def put(obj: dict[str, Any]) -> dict[str, Any]:
    ticker = str(obj.get("ticker") or "").upper()
    if not ticker:
        raise ValueError("company intelligence object requires ticker")
    with _LOCK:
        _OBJECTS[ticker] = deepcopy(obj)
        return deepcopy(_OBJECTS[ticker])


def get(ticker: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _OBJECTS.get(str(ticker or "").upper())
        return deepcopy(row) if row else None


def list_all() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_OBJECTS.items())]


def count() -> int:
    with _LOCK:
        return len(_OBJECTS)


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(summary))
        if len(_RUNS) > 50:
            del _RUNS[:-50]


def last_run() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_RUNS[-1]) if _RUNS else None
