"""Knowledge confidence and freshness scoring."""

from __future__ import annotations

import datetime as _dt
from typing import Any


def freshness_score(
    updated_at: _dt.datetime | None,
    *,
    as_of: _dt.datetime | None = None,
    half_life_days: float = 90.0,
) -> float:
    if updated_at is None:
        return 0.35
    now = as_of or _dt.datetime.now(_dt.timezone.utc)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=_dt.timezone.utc)
    age_days = max(0.0, (now - updated_at).total_seconds() / 86400.0)
    # Exponential decay
    import math

    score = math.exp(-age_days / max(1.0, half_life_days))
    return round(max(0.05, min(1.0, score)), 4)


def confidence_score(
    *,
    has_thesis: bool = False,
    n_sources: int = 0,
    source_reliability: float = 0.7,
    n_structured_fields: int = 0,
    has_house_view: bool = False,
    has_predictions: bool = False,
) -> float:
    score = 0.25
    score += 0.15 * bool(has_thesis)
    score += min(0.25, 0.05 * max(0, n_sources))
    score += 0.15 * max(0.0, min(1.0, source_reliability))
    score += min(0.15, 0.02 * max(0, n_structured_fields))
    score += 0.05 * bool(has_house_view)
    score += 0.05 * bool(has_predictions)
    return round(max(0.05, min(0.98, score)), 4)


def source_reliability(source: str | None) -> float:
    s = (source or "").lower()
    table = {
        "agi": 0.95,
        "agi_research": 0.95,
        "agi_note": 0.9,
        "broker": 0.8,
        "filing": 0.9,
        "sec": 0.9,
        "nse": 0.9,
        "bse": 0.9,
        "newsletter": 0.55,
        "news": 0.5,
        "seed": 0.65,
        "catalog": 0.65,
    }
    for key, val in table.items():
        if key in s:
            return val
    return 0.6


def count_filled(fields: list[Any]) -> int:
    n = 0
    for f in fields:
        if isinstance(f, str) and f.strip():
            n += 1
        elif isinstance(f, list) and f:
            n += 1
        elif isinstance(f, dict) and f:
            n += 1
    return n
