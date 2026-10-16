"""Conviction engine — per-domain and overall thesis conviction."""

from __future__ import annotations

from typing import Any

from thesis_engine.schema import THESIS_STATES

# Weight of each pillar in overall conviction
_PILLAR_WEIGHTS: dict[str, float] = {
    "Business Quality": 0.22,
    "Financial Quality": 0.2,
    "Valuation": 0.2,
    "Competitive Position": 0.13,
    "Macro Alignment": 0.1,
    "Capital Allocation": 0.08,
    "Portfolio Fit": 0.07,
}


def compute_conviction(
    pillars: list[dict[str, Any]],
    *,
    contradictions: dict[str, Any] | None = None,
    catalysts_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_name = {p["pillar"]: p for p in pillars}

    def _conv(name: str) -> float:
        p = by_name.get(name)
        if not p:
            return 0.5
        # Conviction blends belief strength with confidence in that belief
        return round(0.7 * float(p["strength"]) + 0.3 * float(p["confidence"]), 4)

    business = _conv("Business Quality")
    financial = _conv("Financial Quality")
    valuation = _conv("Valuation")
    macro = _conv("Macro Alignment")
    competitive = _conv("Competitive Position")
    capital = _conv("Capital Allocation")
    portfolio = _conv("Portfolio Fit")

    weighted = 0.0
    for name, weight in _PILLAR_WEIGHTS.items():
        weighted += weight * _conv(name)

    # Penalise unresolved contradictions and negative catalyst skew
    contradictions = contradictions or {}
    penalty = min(0.12, 0.02 * int(contradictions.get("major_count") or 0))
    skew = float((catalysts_summary or {}).get("net_skew") or 0.0)
    weighted = weighted - penalty + 0.05 * skew
    overall = round(max(0.05, min(0.95, weighted)), 4)

    return {
        "business": business,
        "financial": financial,
        "valuation": valuation,
        "macro": macro,
        "competitive": competitive,
        "capital_allocation": capital,
        "portfolio": portfolio,
        "overall": overall,
        "overall_pct": round(overall * 100),
        "contradiction_penalty": round(penalty, 4),
        "catalyst_skew_adjustment": round(0.05 * skew, 4),
        "weights": dict(_PILLAR_WEIGHTS),
    }


def thesis_state(
    overall_conviction: float,
    *,
    supported_pillars: int,
    major_contradictions: int,
    broken: bool = False,
) -> str:
    if broken:
        return "Broken"
    c = float(overall_conviction)
    if c < 0.32:
        return "Rejected"
    if c < 0.42:
        return "Broken" if major_contradictions >= 4 else "Weakening"
    if c < 0.52:
        return "Weakening" if major_contradictions >= 3 else "Emerging"
    if c < 0.6:
        return "Developing"
    if c < 0.72:
        return "Strong" if supported_pillars >= 4 else "Developing"
    state = "Very Strong" if supported_pillars >= 5 else "Strong"
    assert state in THESIS_STATES
    return state
