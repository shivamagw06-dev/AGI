"""Long-term Business Analyst opinion timeline — every opinion stored with outcome hooks."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any


_LOCK = Lock()
_TIMELINE: dict[str, list[dict[str, Any]]] = {}  # ticker -> opinions


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_opinion(
    ticker: str | None,
    *,
    year: int | None = None,
    business_quality_score: float | None = None,
    quality_grade: str | None = None,
    moat: str | None = None,
    stance: str | None = None,
    reason: str | None = None,
    evidence: list[str] | None = None,
    outcome: str | None = None,
    accuracy: float | None = None,
    trajectory: str | None = None,
) -> dict[str, Any] | None:
    if not ticker:
        return None
    t = ticker.upper()
    row = {
        "recorded_at": _now(),
        "year": year or datetime.now(timezone.utc).year,
        "business_quality": business_quality_score,
        "quality_grade": quality_grade,
        "moat": moat,
        "stance": stance,
        "reason": (reason or "")[:320],
        "evidence": list(evidence or [])[:6],
        "outcome": outcome,
        "accuracy": accuracy,
        "trajectory": trajectory,
    }
    with _LOCK:
        hist = _TIMELINE.setdefault(t, [])
        hist.append(row)
        if len(hist) > 80:
            del hist[:-80]
    return deepcopy(row)


def get_timeline(ticker: str | None, *, limit: int = 20) -> list[dict[str, Any]]:
    if not ticker:
        return []
    t = ticker.upper()
    with _LOCK:
        rows = list(_TIMELINE.get(t) or [])
    return deepcopy(rows[-limit:])


def quality_series(ticker: str | None) -> list[dict[str, Any]]:
    """Collapse opinion timeline into year → business quality points."""
    rows = get_timeline(ticker, limit=40)
    by_year: dict[int, dict[str, Any]] = {}
    for row in rows:
        y = int(row.get("year") or 0)
        if not y:
            continue
        score = row.get("business_quality")
        if score is None:
            continue
        by_year[y] = {"year": y, "business_quality": float(score), "grade": row.get("quality_grade")}
    return [by_year[y] for y in sorted(by_year)]


def reset_for_tests() -> None:
    with _LOCK:
        _TIMELINE.clear()
