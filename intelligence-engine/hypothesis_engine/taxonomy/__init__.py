"""Hypothesis taxonomy — types, default owners, impact weights."""

from __future__ import annotations

from typing import Any

from hypothesis_engine.schema import HYPOTHESIS_TYPES

TYPE_OWNERS: dict[str, list[str]] = {
    "Business": ["Business"],
    "Financial": ["Financial"],
    "Valuation": ["Valuation"],
    "Macro": ["Macro"],
    "Risk": ["Risk"],
    "Portfolio": ["Portfolio"],
    "Management": ["Management"],
    "Accounting": ["Accounting"],
    "Industry": ["Sector", "Business"],
    "Competitive": ["Sector", "Business"],
    "Capital Allocation": ["Financial", "Management"],
    "Forecast": ["Forecast"],
}

# Default expected-impact ranking weights by type (investment evaluation)
DEFAULT_IMPACT_WEIGHTS: dict[str, float] = {
    "Valuation": 0.32,
    "Business": 0.28,
    "Financial": 0.20,
    "Macro": 0.10,
    "Risk": 0.10,
    "Competitive": 0.08,
    "Industry": 0.08,
    "Forecast": 0.08,
    "Portfolio": 0.07,
    "Management": 0.06,
    "Accounting": 0.06,
    "Capital Allocation": 0.07,
}

OBJECTIVE_TYPE_FOCUS: dict[str, list[str]] = {
    "investment evaluation": ["Business", "Financial", "Valuation", "Risk", "Competitive", "Forecast"],
    "decision_support": ["Business", "Financial", "Valuation", "Risk", "Portfolio"],
    "peer comparison": ["Competitive", "Business", "Financial", "Valuation", "Industry"],
    "comparison_assessment": ["Competitive", "Business", "Financial", "Valuation"],
    "historical analysis": ["Valuation", "Macro", "Industry", "Forecast"],
    "valuation_assessment": ["Valuation", "Financial", "Business", "Macro"],
    "macro impact": ["Macro", "Industry", "Forecast", "Risk"],
    "forecast_assessment": ["Forecast", "Macro", "Financial"],
    "portfolio decision": ["Portfolio", "Risk", "Valuation", "Macro"],
    "portfolio_assessment": ["Portfolio", "Risk", "Valuation"],
    "risk assessment": ["Risk", "Financial", "Macro", "Accounting"],
    "risk_assessment": ["Risk", "Financial", "Macro"],
    "educational": ["Business", "Financial"],
    "educational_explanation": ["Financial", "Business"],
    "accounting review": ["Accounting", "Financial", "Risk"],
    "management assessment": ["Management", "Capital Allocation", "Business"],
}


def owners_for(hypothesis_type: str) -> list[str]:
    return list(TYPE_OWNERS.get(hypothesis_type, ["Business"]))


def focus_types(primary_objective: str | None, question: str) -> list[str]:
    obj = (primary_objective or "").strip().lower()
    q = (question or "").lower()
    if obj in OBJECTIVE_TYPE_FOCUS:
        return list(OBJECTIVE_TYPE_FOCUS[obj])
    if "explain" in q or "what is" in q:
        return list(OBJECTIVE_TYPE_FOCUS["educational"])
    if "compare" in q or " vs " in q:
        return list(OBJECTIVE_TYPE_FOCUS["peer comparison"])
    if "versus history" in q or "expensive" in q:
        return list(OBJECTIVE_TYPE_FOCUS["historical analysis"])
    if "portfolio" in q:
        return list(OBJECTIVE_TYPE_FOCUS["portfolio decision"])
    if "rbi" in q or "macro" in q or "rate cut" in q:
        return list(OBJECTIVE_TYPE_FOCUS["macro impact"])
    if "risk" in q:
        return list(OBJECTIVE_TYPE_FOCUS["risk assessment"])
    return list(OBJECTIVE_TYPE_FOCUS["investment evaluation"])


def taxonomy_stats() -> dict[str, Any]:
    return {
        "type_count": len(HYPOTHESIS_TYPES),
        "types": list(HYPOTHESIS_TYPES),
        "default_impact_weights": dict(DEFAULT_IMPACT_WEIGHTS),
    }
