"""Process-local analyst opinion + committee minutes memory (not an engine)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any


_LOCK = Lock()
_OPINIONS: dict[str, dict[str, dict[str, Any]]] = {}  # ticker -> role -> opinion
_MINUTES: dict[str, list[dict[str, Any]]] = {}  # ticker -> minutes history


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_previous_opinion(ticker: str | None, role: str) -> dict[str, Any] | None:
    if not ticker:
        return None
    t = ticker.upper()
    with _LOCK:
        row = (_OPINIONS.get(t) or {}).get(role)
        return deepcopy(row) if row else None


def put_opinion(ticker: str | None, role: str, opinion: dict[str, Any]) -> None:
    if not ticker:
        return
    t = ticker.upper()
    slim = {
        "role": role,
        "summary": opinion.get("summary") or opinion.get("headline"),
        "stance": opinion.get("stance"),
        "strengths": list(opinion.get("strengths") or [])[:4],
        "weaknesses": list(opinion.get("weaknesses") or [])[:4],
        "confidence": opinion.get("confidence"),
        "recorded_at": _now(),
    }
    with _LOCK:
        _OPINIONS.setdefault(t, {})[role] = slim


def put_opinions(ticker: str | None, opinions: dict[str, dict[str, Any]]) -> None:
    for role, op in (opinions or {}).items():
        if isinstance(op, dict):
            put_opinion(ticker, role, op)


def get_minutes_history(ticker: str | None, *, limit: int = 8) -> list[dict[str, Any]]:
    if not ticker:
        return []
    t = ticker.upper()
    with _LOCK:
        rows = list(_MINUTES.get(t) or [])
    return deepcopy(rows[-limit:])


def put_minutes(ticker: str | None, minutes: dict[str, Any]) -> dict[str, Any]:
    if not ticker:
        return minutes
    t = ticker.upper()
    row = {**deepcopy(minutes), "ticker": t, "recorded_at": _now()}
    with _LOCK:
        hist = _MINUTES.setdefault(t, [])
        hist.append(row)
        if len(hist) > 40:
            del hist[:-40]
    return row


def reset_for_tests() -> None:
    with _LOCK:
        _OPINIONS.clear()
        _MINUTES.clear()


def metrics() -> dict[str, Any]:
    with _LOCK:
        return {
            "tickers_with_opinions": len(_OPINIONS),
            "tickers_with_minutes": len(_MINUTES),
            "opinion_slots": sum(len(v) for v in _OPINIONS.values()),
            "minutes_events": sum(len(v) for v in _MINUTES.values()),
        }
