"""Process-local Business DNA store — knowledge asset persistence, not an engine."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any


_LOCK = Lock()
_DNA: dict[str, dict[str, Any]] = {}  # ticker -> dna
_HISTORY: dict[str, list[dict[str, Any]]] = {}  # ticker -> dna snapshots


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_dna(ticker: str | None) -> dict[str, Any] | None:
    if not ticker:
        return None
    t = ticker.upper()
    with _LOCK:
        row = _DNA.get(t)
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
                "moat": row.get("moat"),
                "pricing_power": row.get("pricing_power"),
                "quality_grade": row.get("quality_grade"),
                "risk_profile": row.get("risk_profile"),
                "summary": row.get("summary"),
            }
        )
        if len(hist) > 40:
            del hist[:-40]
    return row


def get_dna_history(ticker: str | None, *, limit: int = 12) -> list[dict[str, Any]]:
    if not ticker:
        return []
    t = ticker.upper()
    with _LOCK:
        rows = list(_HISTORY.get(t) or [])
    return deepcopy(rows[-limit:])


def reset_for_tests() -> None:
    with _LOCK:
        _DNA.clear()
        _HISTORY.clear()
