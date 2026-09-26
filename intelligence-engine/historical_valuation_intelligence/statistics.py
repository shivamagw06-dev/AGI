"""Rolling historical statistics, bands, percentiles — query-time only."""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from historical_valuation_intelligence.models import MIN_STATS_OBS, REGIME_BANDS, WINDOWS


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        out = float(value)
        return None if out != out else out
    except (TypeError, ValueError):
        return None


def window_floor(window: Optional[str]) -> Optional[str]:
    days = WINDOWS.get(str(window or "max").lower())
    if not days:
        return None
    return (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()


def filter_points(
    points: list[dict[str, Any]],
    *,
    window: str = "max",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[dict[str, Any]]:
    floor = start or window_floor(window)
    out = []
    for p in points:
        period = str(p.get("period") or p.get("date") or "")
        value = _num(p.get("value"))
        if not period or value is None:
            continue
        if floor and period < floor:
            continue
        if end and period > end:
            continue
        out.append({"period": period, "date": period, "value": value, "source": p.get("source")})
    out.sort(key=lambda x: x["period"])
    return out


def _percentile_of(value: float, values: list[float]) -> float:
    if not values:
        return 0.0
    return round(100.0 * sum(1 for v in values if v <= value) / len(values), 1)


def _quantile(ordered: list[float], q: float) -> Optional[float]:
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def compute_stats(points: list[dict[str, Any]]) -> dict[str, Any]:
    values = [p["value"] for p in points if _num(p.get("value")) is not None]
    if not values:
        return {
            "ok": False,
            "observation_count": 0,
            "coverage_pct": 0.0,
        }
    ordered = sorted(values)
    current = values[-1]
    mean = sum(values) / len(values)
    variance = (
        sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        if len(values) > 1
        else 0.0
    )
    stdev = math.sqrt(variance)
    z = round((current - mean) / stdev, 3) if stdev > 0 else 0.0
    median = statistics.median(values)
    p25 = _quantile(ordered, 0.25)
    p75 = _quantile(ordered, 0.75)
    current_pct = _percentile_of(current, values)
    premium = round(100.0 * (current - median) / abs(median), 2) if median else None
    first_period = points[0]["period"]
    last_period = points[-1]["period"]
    try:
        span_days = (
            datetime.fromisoformat(last_period[:10]) - datetime.fromisoformat(first_period[:10])
        ).days
        span_years = round(span_days / 365.25, 2)
    except Exception:
        span_years = None

    return {
        "ok": True,
        "observation_count": len(values),
        "min": round(ordered[0], 4),
        "max": round(ordered[-1], 4),
        "mean": round(mean, 4),
        "median": round(median, 4),
        "stdev": round(stdev, 4),
        "variance": round(variance, 4),
        "p25": round(p25, 4) if p25 is not None else None,
        "p75": round(p75, 4) if p75 is not None else None,
        "current": round(current, 4),
        "current_percentile": current_pct,
        "z_score": z,
        "premium_to_median_pct": premium,
        "first": first_period,
        "last": last_period,
        "span_years": span_years,
        "coverage_pct": 100.0,  # among non-null observations in the filtered window
        "sufficient": len(values) >= MIN_STATS_OBS,
    }


def bands_from_stats(stats: dict[str, Any]) -> dict[str, Any]:
    if not stats.get("ok"):
        return {"ok": False, "error": "no_stats"}
    return {
        "ok": True,
        "min": stats["min"],
        "p25": stats["p25"],
        "median": stats["median"],
        "p75": stats["p75"],
        "max": stats["max"],
        "current": stats["current"],
        "observation_count": stats["observation_count"],
    }


def regime_from_percentile(percentile: Optional[float]) -> dict[str, Any]:
    if percentile is None:
        return {"regime": "UNKNOWN", "percentile": None}
    for lo, hi, label in REGIME_BANDS:
        if lo <= percentile < hi:
            return {"regime": label, "percentile": percentile}
    return {"regime": "VERY_EXPENSIVE", "percentile": percentile}


def all_window_stats(points: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for window in WINDOWS:
        filtered = filter_points(points, window=window)
        out[window] = compute_stats(filtered)
    return out
