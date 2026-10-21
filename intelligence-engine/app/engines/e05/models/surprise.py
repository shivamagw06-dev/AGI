"""Basic earnings / guidance surprise scoring (P0 — no probabilistic deal models)."""

from __future__ import annotations

import math


def eps_surprise(actual: float | None, consensus: float | None, *, eps: float = 1e-6) -> float | None:
    """(A − C) / max(|C|, ε). None when inputs missing."""
    if actual is None or consensus is None:
        return None
    denom = max(abs(float(consensus)), eps)
    return round((float(actual) - float(consensus)) / denom, 8)


def surprise_score_0_100(surp: float | None) -> float:
    """Map surprise ratio → [0, 100] via tanh (50 = in-line)."""
    if surp is None:
        return 50.0
    # winsorise extremes
    x = max(-0.5, min(0.5, float(surp)))
    return round(50.0 + 50.0 * math.tanh(x * 4.0), 6)


def signed_impact(surp: float | None, importance: float) -> float:
    """Signed expected impact in [-100, 100]."""
    if surp is None:
        return 0.0
    x = max(-0.5, min(0.5, float(surp)))
    return round(100.0 * math.tanh(x * 4.0) * max(0.0, min(1.0, importance)), 6)


def guidance_delta_score(delta: float | None) -> float:
    """Guidance % delta → [0, 100]."""
    if delta is None:
        return 50.0
    x = max(-0.5, min(0.5, float(delta)))
    return round(50.0 + 50.0 * math.tanh(x * 3.0), 6)
