"""Map research objective → required / optional / suppressed analysts."""

from __future__ import annotations

from typing import Any

from analyst_router.schema import ANALYST_REGISTRY

# Primary objective → (required, optional)
# Suppressed = registry − required − optional
_OBJECTIVE_ROUTES: dict[str, dict[str, list[str]]] = {
    "Investment Evaluation": {
        "required": ["Business", "Financial", "Valuation", "Risk", "Forecast", "Portfolio"],
        "optional": ["Macro"],
    },
    "Valuation Assessment": {
        "required": ["Valuation", "Financial"],
        "optional": ["Sector", "Macro"],
    },
    "Business Quality Assessment": {
        "required": ["Business", "Management"],
        "optional": ["Financial", "Sector"],
    },
    "Financial Health Assessment": {
        "required": ["Financial", "Accounting", "Risk"],
        "optional": [],
    },
    "Risk Assessment": {
        "required": ["Risk", "Financial", "Macro"],
        "optional": ["Portfolio"],
    },
    "Portfolio Decision": {
        "required": ["Portfolio", "Risk", "Valuation"],
        "optional": ["Business", "Forecast", "Macro"],
    },
    "Sector Attractiveness": {
        "required": ["Sector", "Macro", "Valuation"],
        "optional": ["Forecast"],
    },
    "Industry Structure": {
        "required": ["Sector", "Business"],
        "optional": ["Financial"],
    },
    "Macro Impact": {
        "required": ["Macro", "Sector", "Forecast", "Risk"],
        "optional": ["Financial"],
    },
    "Historical Analysis": {
        "required": ["Valuation", "Sector", "Macro", "Forecast"],
        "optional": [],
    },
    "Peer Comparison": {
        "required": ["Business", "Financial", "Valuation", "Sector"],
        "optional": [],
    },
    "Scenario Analysis": {
        "required": ["Forecast", "Risk", "Macro"],
        "optional": ["Valuation", "Business"],
    },
    "Forecast": {
        "required": ["Forecast", "Financial", "Macro"],
        "optional": ["Business"],
    },
    "News Impact": {
        "required": ["News", "Risk"],
        "optional": ["Macro", "Market"],
    },
    "Event Analysis": {
        "required": ["News", "Financial"],
        "optional": ["Market", "Risk"],
    },
    "Screening": {
        "required": ["Financial", "Valuation", "Sector"],
        "optional": ["Macro"],
    },
    "Educational": {
        "required": ["Academy", "Financial"],
        "optional": [],
    },
    "Technical Analysis": {
        "required": ["Market", "Risk"],
        "optional": [],
    },
    "Accounting Review": {
        "required": ["Accounting", "Financial"],
        "optional": ["Risk"],
    },
    "Management Assessment": {
        "required": ["Management", "Business"],
        "optional": ["Ownership"],
    },
    "Ownership Review": {
        "required": ["Ownership"],
        "optional": ["Management"],
    },
    "Governance Review": {
        "required": ["Management", "Ownership"],
        "optional": ["Accounting"],
    },
    "Policy Analysis": {
        "required": ["Macro", "Sector"],
        "optional": ["Risk"],
    },
    "Regulatory Analysis": {
        "required": ["Macro", "Risk"],
        "optional": ["Sector"],
    },
}

# Committee / CIO join investment-style workflows as synthesis (not in "required specialists"
# examples for HDFC, but appear in speaking order for company research).
_SYNTHESIS_OBJECTIVES = frozenset(
    {
        "Investment Evaluation",
        "Portfolio Decision",
        "Scenario Analysis",
    }
)


def participate(
    primary_objective: str | None,
    *,
    question_type: str | None = None,
    depth: str | None = None,
) -> dict[str, Any]:
    obj = primary_objective or ""
    route = _OBJECTIVE_ROUTES.get(obj)
    if not route:
        # Weak fallback — never invite everyone
        required = ["Financial"]
        optional: list[str] = []
        confidence = 0.7
    else:
        required = list(route["required"])
        optional = list(route["optional"])
        confidence = 0.98

    # Educational: Academy + Financial only (sprint example)
    if obj == "Educational" or question_type in {"Explain", "Teach"}:
        required = ["Academy", "Financial"]
        optional = []
        confidence = 0.99

    # Institutional buy/sell adds committee synthesis to speaking path via optional→required elev
    synthesis: list[str] = []
    if obj in _SYNTHESIS_OBJECTIVES or question_type in {"Should I Buy?", "Should I Sell?"}:
        synthesis = ["Committee", "CIO"]

    selected = set(required) | set(optional) | set(synthesis)
    suppressed = [a for a in ANALYST_REGISTRY if a not in selected]

    # Explicit suppressions called out in sprint examples
    if obj == "Investment Evaluation":
        for a in ("Ownership", "Academy"):
            if a not in suppressed and a not in required and a not in optional:
                suppressed.append(a)
    if obj == "Peer Comparison":
        for a in ("Portfolio", "Management"):
            if a in optional:
                optional = [x for x in optional if x != a]
            if a not in suppressed and a not in required:
                suppressed.append(a)
                selected.discard(a)
        suppressed = [a for a in ANALYST_REGISTRY if a not in (set(required) | set(optional) | set(synthesis))]
    if obj == "Historical Analysis":
        for a in ("Business", "Management", "Portfolio"):
            if a in required:
                required = [x for x in required if x != a]
            if a in optional:
                optional = [x for x in optional if x != a]
        selected = set(required) | set(optional) | set(synthesis)
        suppressed = [a for a in ANALYST_REGISTRY if a not in selected]
    if obj == "Educational":
        synthesis = []
        selected = set(required) | set(optional)
        suppressed = [a for a in ANALYST_REGISTRY if a not in selected]
        # Ensure Committee suppressed
        if "Committee" not in suppressed:
            suppressed.append("Committee")

    # Depth: Continuous Monitoring may add Market optional
    if depth == "Continuous Monitoring" and "Market" not in required and "Market" not in optional:
        optional.append("Market")
        if "Market" in suppressed:
            suppressed = [a for a in suppressed if a != "Market"]

    return {
        "required_analysts": required,
        "optional_analysts": optional,
        "suppressed_analysts": suppressed,
        "synthesis_analysts": synthesis,
        "participation_confidence": confidence,
        "map_version": "iar-v1",
    }
