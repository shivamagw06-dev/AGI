"""Process-local Financial DNA store."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK = Lock()
_DNA: dict[str, dict[str, Any]] = {}
_HISTORY: dict[str, list[dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    row = {**deepcopy(dna), "ticker": t, "recorded_at": _now()}
    with _LOCK:
        _DNA[t] = row
        hist = _HISTORY.setdefault(t, [])
        hist.append(
            {
                "recorded_at": row["recorded_at"],
                "margin_profile": row.get("margin_profile"),
                "cash_generation": row.get("cash_generation"),
                "return_profile": row.get("return_profile"),
                "financial_durability": row.get("financial_durability"),
            }
        )
        if len(hist) > 40:
            del hist[:-40]
    return row


def reset_for_tests() -> None:
    with _LOCK:
        _DNA.clear()
        _HISTORY.clear()
