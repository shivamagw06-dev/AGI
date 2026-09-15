"""Deterministic exponential decay — w = exp(-λ · age_days), λ = ln2 / HL."""

from __future__ import annotations

import math

from app.engines.e11.mapping import NEWS_HALF_LIFE_DAYS


def decay_weight(*, age_hours: float, half_life_days: float = NEWS_HALF_LIFE_DAYS) -> float:
    hl = max(0.25, float(half_life_days))
    age_days = max(0.0, float(age_hours)) / 24.0
    w = math.exp(-(math.log(2.0) / hl) * age_days)
    return round(max(0.0, min(1.0, w)), 8)
