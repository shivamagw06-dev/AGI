"""Shared metric helpers for IAT — numbers only, no decision changes."""

from __future__ import annotations

from statistics import mean
from typing import Any


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pct(n: int, d: int) -> float | None:
    if d <= 0:
        return None
    return round(100.0 * n / d, 1)


def avg(vals: list[float | None]) -> float | None:
    clean = [float(v) for v in vals if v is not None]
    if not clean:
        return None
    return round(mean(clean), 2)


def p95(vals: list[float]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round(0.95 * (len(s) - 1)))))
    return round(s[idx], 3)


def as_0_10(v: Any) -> float | None:
    """Normalise quality scores that may be 0–10 or 0–100."""
    n = _num(v)
    if n is None:
        return None
    if n > 10.0:
        return round(n / 10.0, 2)
    return round(n, 2)


def as_pct(v: Any) -> float | None:
    """Normalise readiness/confidence that may be 0–1 or 0–100."""
    n = _num(v)
    if n is None:
        return None
    if 0.0 <= n <= 1.0:
        return round(n * 100.0, 1)
    return round(n, 1)
