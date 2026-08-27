"""Thesis stability — trend and volatility, not a single conviction snapshot."""

from __future__ import annotations

from statistics import pstdev
from typing import Any


def assess_stability(
    current_conviction: float,
    *,
    prior_snapshots: list[dict[str, Any]] | None = None,
    pillar_strengths: list[float] | None = None,
) -> dict[str, Any]:
    history = list(prior_snapshots or [])
    values = []
    for item in history:
        if not isinstance(item, dict):
            continue
        value = item.get("conviction")
        if isinstance(value, dict):
            value = value.get("overall")
        if value is not None:
            values.append(float(value))
    values.append(float(current_conviction))

    volatility = pstdev(values) if len(values) > 1 else 0.0
    delta = values[-1] - values[-2] if len(values) > 1 else 0.0
    pillar_dispersion = pstdev(list(pillar_strengths or [])) if len(pillar_strengths or []) > 1 else 0.0
    score = max(0.0, min(1.0, 1.0 - 2.4 * volatility - 0.8 * pillar_dispersion))

    if len(values) == 1:
        trend = "Stable"
    elif volatility >= 0.12:
        trend = "Volatile"
    elif delta >= 0.035:
        trend = "Improving"
    elif delta <= -0.035:
        trend = "Weakening"
    else:
        trend = "Stable"

    classification = "Stable" if score >= 0.72 else "Moderate" if score >= 0.48 else "Fragile"
    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "classification": classification,
        "trend": trend,
        "volatility": round(volatility, 4),
        "pillar_dispersion": round(pillar_dispersion, 4),
        "latest_delta": round(delta, 4),
        "observations": len(values),
        "conviction_history": [round(v, 4) for v in values[-12:]],
    }
