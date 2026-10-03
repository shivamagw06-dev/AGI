"""Trend intelligence — derived only from observed numeric values."""

from __future__ import annotations

import math
from typing import Any

from knowledge_factory.alternative_data_intelligence.schema import IADI_VERSION, UNKNOWN


def compute_trends(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute trend / momentum / seasonality from validated observations only."""
    values: list[float] = []
    dates: list[str] = []
    for o in sorted(observations, key=lambda x: x.get("date") or ""):
        raw = (o.get("observation") or {}).get("value")
        if raw is None or raw == UNKNOWN:
            continue
        try:
            values.append(float(raw))
            dates.append(str(o.get("date")))
        except (TypeError, ValueError):
            continue

    n = len(values)
    if n < 3:
        return {
            "status": "insufficient_observations",
            "n": n,
            "trend": UNKNOWN,
            "momentum": UNKNOWN,
            "acceleration": UNKNOWN,
            "seasonality": UNKNOWN,
            "rolling_average": UNKNOWN,
            "historical_percentile": UNKNOWN,
            "historical_extremes": UNKNOWN,
            "volatility": UNKNOWN,
            "version": IADI_VERSION,
            "fabricated": False,
            "derived_from_observations_only": True,
        }

    latest = values[-1]
    prev = values[-2]
    prev2 = values[-3]
    window = values[-min(12, n) :]
    rolling = sum(window) / len(window)

    # Simple momentum: % change latest vs prior
    momentum = ((latest - prev) / abs(prev)) if prev != 0 else 0.0
    prior_mom = ((prev - prev2) / abs(prev2)) if prev2 != 0 else 0.0
    acceleration = momentum - prior_mom

    # Trend: compare latest rolling to earlier half mean
    mid = max(n // 2, 1)
    early = sum(values[:mid]) / mid
    late = sum(values[mid:]) / max(n - mid, 1)
    if late > early * 1.02:
        trend = "rising"
    elif late < early * 0.98:
        trend = "falling"
    else:
        trend = "stable"

    # Seasonality proxy: variance of month-of-year means if enough history
    seasonality = UNKNOWN
    if n >= 24:
        buckets: dict[int, list[float]] = {}
        for d, v in zip(dates, values):
            try:
                m = int(d[5:7])
            except Exception:
                continue
            buckets.setdefault(m, []).append(v)
        means = [sum(vs) / len(vs) for vs in buckets.values() if vs]
        if means:
            mu = sum(means) / len(means)
            var = sum((x - mu) ** 2 for x in means) / len(means)
            seasonality = "present" if var > (mu * 0.01) ** 2 else "low"

    # Historical percentile of latest
    below = sum(1 for v in values if v <= latest)
    percentile = round(100.0 * below / n, 2)

    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    volatility = round(math.sqrt(variance), 4)

    return {
        "status": "ok",
        "n": n,
        "latest_date": dates[-1],
        "latest_value": latest,
        "trend": trend,
        "momentum": round(momentum, 6),
        "acceleration": round(acceleration, 6),
        "seasonality": seasonality,
        "rolling_average": round(rolling, 4),
        "rolling_window": len(window),
        "historical_percentile": percentile,
        "historical_extremes": {"min": min(values), "max": max(values)},
        "volatility": volatility,
        "version": IADI_VERSION,
        "fabricated": False,
        "derived_from_observations_only": True,
        "prediction": False,
    }
