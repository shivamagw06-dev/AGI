"""Process-local Valuation DNA store."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK = Lock()
_DNA: dict[str, dict[str, Any]] = {}


def get_dna(ticker: str | None) -> dict[str, Any] | None:
    if not ticker:
        return None
    with _LOCK:
        row = _DNA.get(ticker.upper())
        return deepcopy(row) if row else None


def put_dna(ticker: str | None, dna: dict[str, Any]) -> dict[str, Any]:
    if not ticker:
        return dna
    t = ticker.upper()
    row = {**deepcopy(dna), "ticker": t, "recorded_at": datetime.now(timezone.utc).isoformat()}
    with _LOCK:
        _DNA[t] = row
    return row


def reset_for_tests() -> None:
    with _LOCK:
        _DNA.clear()
