"""Exact conviction waterfall showing what drives the final score."""

from __future__ import annotations

from typing import Any

_DISPLAY_NAMES = {
    "Business Quality": "Business",
    "Financial Quality": "Financial",
    "Capital Allocation": "Capital Allocation",
    "Competitive Position": "Competitive",
    "Valuation": "Valuation",
    "Macro Alignment": "Macro",
    "Portfolio Fit": "Portfolio",
}


def build_conviction_waterfall(
    pillars: list[dict[str, Any]],
    conviction: dict[str, Any],
    *,
    pressure_penalties: dict[str, float] | None = None,
) -> dict[str, Any]:
    starting = 0.5
    weights = conviction.get("weights") or {}
    steps = []
    running = starting
    for p in pillars:
        name = p["pillar"]
        weight = float(weights.get(name, 0.0))
        impact = weight * (float(p.get("strength") or 0.5) - 0.5)
        impact = round(impact, 4)
        running += impact
        steps.append(
            {
                "driver": _DISPLAY_NAMES.get(name, name),
                "pillar": name,
                "impact": impact,
                "impact_pp": round(impact * 100, 1),
                "direction": "Positive" if impact >= 0 else "Negative",
                "running_conviction": round(running, 4),
            }
        )

    for driver, penalty in (pressure_penalties or {}).items():
        impact = -abs(float(penalty))
        running += impact
        steps.append(
            {
                "driver": driver,
                "pillar": None,
                "impact": round(impact, 4),
                "impact_pp": round(impact * 100, 1),
                "direction": "Negative",
                "running_conviction": round(running, 4),
            }
        )

    target = float(conviction.get("overall") or running)
    reconciliation = round(target - running, 4)
    if reconciliation:
        running += reconciliation
        steps.append(
            {
                "driver": "Calibration & Catalyst Adjustment",
                "pillar": None,
                "impact": reconciliation,
                "impact_pp": round(reconciliation * 100, 1),
                "direction": "Positive" if reconciliation >= 0 else "Negative",
                "running_conviction": round(running, 4),
            }
        )
    return {
        "starting_conviction": starting,
        "starting_conviction_pct": 50,
        "steps": steps,
        "ending_conviction": round(target, 4),
        "ending_conviction_pct": round(target * 100),
        "reconciles": abs(starting + sum(s["impact"] for s in steps) - target) < 0.001,
    }
