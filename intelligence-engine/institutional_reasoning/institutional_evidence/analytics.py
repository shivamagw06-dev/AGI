"""Module 5 — Historical Analytics.

Compute automatically for every metric series:
  average, median, std, z-score, historical percentile,
  rolling average, premium, discount, trend, volatility.
"""

from __future__ import annotations

import math
from statistics import mean, median, pstdev
from typing import Any

ANALYTICS_VERSION = "historical-analytics-v1.0.0"


def _ordered_values(points: dict[str, float] | None) -> list[tuple[str, float]]:
    if not points:
        return []
    items = [(str(k), float(v)) for k, v in points.items() if v is not None]
    # Period keys like FY17..FY26 / 2017-01 sort lexicographically for FY labels.
    items.sort(key=lambda kv: kv[0])
    return items


def rolling_average(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            chunk = values[i + 1 - window : i + 1]
            out.append(round(sum(chunk) / window, 6))
    return out


def rolling_median(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
        else:
            chunk = values[i + 1 - window : i + 1]
            out.append(round(float(median(chunk)), 6))
    return out


def historical_percentile(current: float, values: list[float]) -> float | None:
    """Percentile of current within the series (inclusive)."""
    if not values:
        return None
    below = sum(1 for v in values if v < current)
    equal = sum(1 for v in values if v == current)
    # Midrank for ties
    rank = below + 0.5 * equal
    return round(100.0 * rank / len(values), 2)


def z_score(current: float, values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mu = mean(values)
    sd = pstdev(values)
    if sd == 0:
        return 0.0
    return round((current - mu) / sd, 4)


def trend_label(values: list[float]) -> str:
    if len(values) < 3:
        return "insufficient"
    half = max(2, len(values) // 2)
    early = mean(values[:half])
    late = mean(values[-half:])
    if early == 0:
        return "stable"
    chg = (late - early) / abs(early)
    if chg > 0.08:
        return "rising"
    if chg < -0.08:
        return "falling"
    return "stable"


def analyse_series(
    points: dict[str, float] | None,
    *,
    current: float | None = None,
    rolling_window: int = 3,
) -> dict[str, Any]:
    """Full analytics block for one metric series."""
    ordered = _ordered_values(points)
    if not ordered:
        return {
            "found": False,
            "n": 0,
            "analytics_version": ANALYTICS_VERSION,
        }
    periods = [p for p, _ in ordered]
    values = [v for _, v in ordered]
    latest = values[-1]
    cur = float(current) if current is not None else latest
    avg = mean(values)
    med = float(median(values))
    sd = pstdev(values) if len(values) > 1 else 0.0
    pctile = historical_percentile(cur, values)
    z = z_score(cur, values)
    premium = round((cur / avg - 1.0) * 100.0, 2) if avg else None
    discount = round((avg / cur - 1.0) * 100.0, 2) if cur else None
    roll_avg = rolling_average(values, rolling_window)
    roll_med = rolling_median(values, rolling_window)

    return {
        "found": True,
        "n": len(values),
        "periods": periods,
        "values": values,
        "latest": latest,
        "latest_period": periods[-1],
        "current": cur,
        "average": round(avg, 4),
        "median": round(med, 4),
        "std_dev": round(sd, 4),
        "historical_high": max(values),
        "historical_low": min(values),
        "historical_percentile": pctile,
        "z_score": z,
        "premium_vs_average_pct": premium,
        "discount_vs_average_pct": discount,
        "rolling_average": roll_avg[-1],
        "rolling_median": roll_med[-1],
        "rolling_window": rolling_window,
        "trend": trend_label(values),
        "volatility": round(sd / abs(avg), 4) if avg else None,
        "coverage_years": len(values),
        "analytics_version": ANALYTICS_VERSION,
    }
