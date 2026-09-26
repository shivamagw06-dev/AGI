"""Canonical event decay kernel — w = exp(-λ · age_days), λ = ln2 / HL."""

from __future__ import annotations

import math

from app.engines.e05.mapping import HALF_LIFE_DAYS


def decay_lambda(half_life_days: float) -> float:
    hl = max(0.5, float(half_life_days))
    return math.log(2.0) / hl


def decay_weight(age_days: float, half_life_days: float) -> float:
    """Intensity weight in (0, 1]. Upcoming events (age < 0) use age=0 (full weight)."""
    age = max(0.0, float(age_days))
    w = math.exp(-decay_lambda(half_life_days) * age)
    return round(max(0.0, min(1.0, w)), 8)


def half_life_for(event_type: str) -> float:
    return float(HALF_LIFE_DAYS.get(event_type, 10.0))
