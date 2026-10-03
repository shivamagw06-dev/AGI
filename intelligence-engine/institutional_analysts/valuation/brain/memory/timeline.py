"""Valuation memory — opinions, multiple/expectation changes, accuracy hooks."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK = Lock()
_TIMELINE: dict[str, list[dict[str, Any]]] = {}


def record_opinion(ticker: str | None, row: dict[str, Any]) -> None:
    if not ticker:
        return
    t = ticker.upper()
    item = {**deepcopy(row), "recorded_at": datetime.now(timezone.utc).isoformat()}
    with _LOCK:
        hist = _TIMELINE.setdefault(t, [])
        hist.append(item)
        if len(hist) > 80:
            del hist[:-80]


def get_timeline(ticker: str | None, *, limit: int = 12) -> list[dict[str, Any]]:
    if not ticker:
        return []
    with _LOCK:
        rows = list(_TIMELINE.get(ticker.upper()) or [])
    return deepcopy(rows[-limit:])


def extract_prior(previous: dict[str, Any] | None) -> dict[str, Any]:
    snap = previous if isinstance(previous, dict) else {}
    return {
        "has_prior": bool(snap),
        "prior_stance": snap.get("stance") if snap else None,
        "prior_summary": snap.get("summary") if snap else None,
    }


def compare(current_stance: str, prior: dict[str, Any], dna_changes: list[str]) -> dict[str, Any]:
    if not prior.get("has_prior"):
        return {"trajectory": "Stable", "what_changed": [], "view_stable": True}
    changes = []
    if prior.get("prior_stance") and prior.get("prior_stance") != current_stance:
        changes.append(f"Stance moved from {prior.get('prior_stance')} to {current_stance}")
    changes.extend(dna_changes[:2])
    traj = "Stable"
    if changes:
        traj = "Improving" if current_stance == "Bullish" else "Deteriorating" if current_stance == "Bearish" else "Stable"
    return {"trajectory": traj, "what_changed": changes, "view_stable": len(changes) == 0}


def reset_for_tests() -> None:
    with _LOCK:
        _TIMELINE.clear()
