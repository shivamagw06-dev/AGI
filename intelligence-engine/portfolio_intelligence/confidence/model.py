"""Portfolio Confidence model.

=
  Holding Coverage (30%)
  + Evidence Quality (25%)
  + Portfolio Data (20%)
  + Risk Coverage (15%)
  + Scenario Coverage (10%)
"""

from __future__ import annotations

from typing import Any

WEIGHTS = {
    "holding_coverage": 0.30,
    "evidence_quality": 0.25,
    "portfolio_data": 0.20,
    "risk_coverage": 0.15,
    "scenario_coverage": 0.10,
}


def portfolio_confidence(
    *,
    holding_coverage: float,
    evidence_quality: float,
    portfolio_data: float,
    risk_coverage: float,
    scenario_coverage: float,
    unknowns: list[str] | None = None,
) -> dict[str, Any]:
    comps = {
        "holding_coverage": max(0.0, min(100.0, holding_coverage)),
        "evidence_quality": max(0.0, min(100.0, evidence_quality)),
        "portfolio_data": max(0.0, min(100.0, portfolio_data)),
        "risk_coverage": max(0.0, min(100.0, risk_coverage)),
        "scenario_coverage": max(0.0, min(100.0, scenario_coverage)),
    }
    contributions = {k: round(comps[k] * WEIGHTS[k], 2) for k in comps}
    total = round(sum(contributions.values()), 2)
    return {
        "confidence": total,
        "breakdown": comps,
        "weights": WEIGHTS,
        "contributions": contributions,
        "explain": (
            f"Holdings {comps['holding_coverage']:.0f}×30% + Evidence {comps['evidence_quality']:.0f}×25% + "
            f"Data {comps['portfolio_data']:.0f}×20% + Risk {comps['risk_coverage']:.0f}×15% + "
            f"Scenarios {comps['scenario_coverage']:.0f}×10% = {total:.0f}"
        ),
        "unknowns": unknowns
        or [
            "Live brokerage lot sync not wired — V1 uses institutional seed books",
            "Holding-level return series for realised correlation pending",
        ],
    }
