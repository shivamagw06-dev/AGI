"""Map primary objective → required institutional analysts."""

from __future__ import annotations

from typing import Any

_MAP: dict[str, list[str]] = {
    "Investment Evaluation": [
        "Business",
        "Financial",
        "Valuation",
        "Risk",
        "Committee",
        "Portfolio",
        "Forecast",
    ],
    "Valuation Assessment": ["Valuation", "Financial", "Peer", "Evidence"],
    "Business Quality Assessment": ["Business", "Management", "Evidence"],
    "Financial Health Assessment": ["Financial", "Accounting", "Risk"],
    "Risk Assessment": ["Risk", "Financial", "Macro", "Evidence"],
    "Portfolio Decision": ["Portfolio", "Risk", "Committee", "Valuation"],
    "Sector Attractiveness": ["Sector", "Macro", "Valuation", "Peer"],
    "Industry Structure": ["Sector", "Business", "Peer"],
    "Macro Impact": ["Macro", "Sector", "Forecast", "Risk"],
    "Historical Analysis": ["Valuation", "Sector", "Macro", "Evidence", "Peer"],
    "Peer Comparison": ["Peer", "Valuation", "Financial", "Business"],
    "Scenario Analysis": ["Forecast", "Risk", "Macro", "Committee"],
    "Forecast": ["Forecast", "Financial", "Macro"],
    "News Impact": ["News", "Evidence", "Risk"],
    "Event Analysis": ["Event", "News", "Evidence"],
    "Screening": ["Peer", "Valuation", "Financial"],
    "Educational": ["Academy"],
    "Technical Analysis": ["Technical", "Risk"],
    "Accounting Review": ["Accounting", "Financial", "Evidence"],
    "Management Assessment": ["Management", "Governance", "Business"],
    "Ownership Review": ["Ownership", "Governance"],
    "Governance Review": ["Governance", "Management", "Ownership"],
    "Policy Analysis": ["Macro", "Sector", "Evidence"],
    "Regulatory Analysis": ["Macro", "Risk", "Governance"],
}


def plan_analysts(primary_objective: str | None, secondary: list[str] | None = None) -> dict[str, Any]:
    analysts = list(_MAP.get(primary_objective or "", ["Evidence"]))
    for sec in secondary or []:
        for a in _MAP.get(sec, []):
            if a not in analysts:
                analysts.append(a)
    # Educational stays academy-only
    if primary_objective == "Educational":
        analysts = ["Academy"]
    return {
        "analysts": analysts,
        "analyst_count": len(analysts),
        "map_version": "roe-v1",
    }
