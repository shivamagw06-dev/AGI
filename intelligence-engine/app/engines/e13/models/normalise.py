"""Cross-sectional winsorise / z-score / percentile for E13 pillars."""

from __future__ import annotations

import math


def _quantile(ordered: list[float], q: float) -> float:
    n = len(ordered)
    if n == 1:
        return ordered[0]
    pos = max(0.0, min(1.0, q)) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    w = pos - lo
    return ordered[lo] * (1.0 - w) + ordered[hi] * w


def winsorise(values: list[float], lo_q: float = 0.025, hi_q: float = 0.975) -> list[float]:
    if not values:
        return []
    ordered = sorted(values)
    lo = _quantile(ordered, lo_q)
    hi = _quantile(ordered, hi_q)
    if hi < lo:
        lo, hi = hi, lo
    return [min(hi, max(lo, v)) for v in values]


def zscore(values: list[float], eps: float = 1e-8) -> list[float | None]:
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return [0.0 if v is not None else None for v in values]
    mu = sum(present) / len(present)
    var = sum((v - mu) ** 2 for v in present) / len(present)
    sigma = math.sqrt(var) + eps
    return [(v - mu) / sigma if v is not None else None for v in values]


def percentile_scores(z_values: list[float | None]) -> list[float | None]:
    indexed = [(i, z) for i, z in enumerate(z_values) if z is not None]
    if not indexed:
        return [None] * len(z_values)
    if len(indexed) == 1:
        out: list[float | None] = [None] * len(z_values)
        out[indexed[0][0]] = 50.0
        return out
    ranked = sorted(indexed, key=lambda t: t[1])
    out = [None] * len(z_values)
    n = len(ranked)
    for rank, (i, _) in enumerate(ranked):
        out[i] = 100.0 * (rank + 1) / n
    return out


def clip_loading(z: float, lo: float = -3.0, hi: float = 3.0) -> float:
    return max(lo, min(hi, z))
