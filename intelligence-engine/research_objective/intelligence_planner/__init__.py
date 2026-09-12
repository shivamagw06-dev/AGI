"""Map objective → required / skipped intelligence layers (plan only)."""

from __future__ import annotations

from typing import Any

from research_objective.schema import ALL_LAYERS

_NEED: dict[str, list[str]] = {
    "Investment Evaluation": ["FIL", "EIL", "PIL", "CIG", "FIE", "Management", "Portfolio", "Accounting"],
    "Valuation Assessment": ["FIL", "EIL", "PIL", "CIG", "FIE"],
    "Business Quality Assessment": ["FIL", "EIL", "CIG", "Management"],
    "Financial Health Assessment": ["FIL", "EIL", "Accounting"],
    "Risk Assessment": ["FIL", "EIL", "PIL", "FIE", "Macro"],
    "Portfolio Decision": ["FIL", "PIL", "Portfolio", "FIE"],
    "Sector Attractiveness": ["FIL", "EIL", "Sector", "Macro", "CIG"],
    "Industry Structure": ["EIL", "Sector", "CIG"],
    "Macro Impact": ["Macro", "Sector", "FIL", "FIE"],
    "Historical Analysis": ["FIL", "EIL", "PIL", "CIG", "FIE"],
    "Peer Comparison": ["FIL", "EIL", "PIL", "CIG"],
    "Scenario Analysis": ["FIL", "FIE", "Macro", "PIL"],
    "Forecast": ["FIL", "FIE", "Macro"],
    "News Impact": ["News", "EIL", "FIE"],
    "Event Analysis": ["News", "EIL", "FIL"],
    "Screening": ["FIL", "EIL", "PIL"],
    "Educational": [],
    "Technical Analysis": ["Technical", "FIL"],
    "Accounting Review": ["Accounting", "FIL", "EIL"],
    "Management Assessment": ["Management", "CIG", "EIL"],
    "Ownership Review": ["CIG", "FIL"],
    "Governance Review": ["CIG", "Management"],
    "Policy Analysis": ["Macro", "Sector", "EIL"],
    "Regulatory Analysis": ["Macro", "EIL", "Accounting"],
}

# Explicit skips called out in the sprint brief for Historical Valuation
_SKIP_HINTS: dict[str, list[str]] = {
    "Historical Analysis": ["Management", "Portfolio", "Accounting"],
    "Educational": list(ALL_LAYERS),
    "Technical Analysis": ["Management", "Accounting", "Portfolio"],
}


def plan_layers(primary_objective: str | None) -> dict[str, Any]:
    need = list(_NEED.get(primary_objective or "", ["FIL", "EIL"]))
    skip_hint = list(_SKIP_HINTS.get(primary_objective or "", []))
    skip = [L for L in ALL_LAYERS if L not in need]
    # Prefer documented skip order when provided
    if skip_hint:
        ordered_skip = [L for L in skip_hint if L in skip] + [L for L in skip if L not in skip_hint]
        skip = ordered_skip
    return {
        "layers": need,
        "layers_required": need,
        "layers_skip": skip,
        "layer_count": len(need),
        "map_version": "roe-v1",
    }
