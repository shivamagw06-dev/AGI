"""Dynamic context importance / prioritisation by objective."""

from __future__ import annotations

from typing import Any

_TEMPLATES: dict[str, dict[str, float]] = {
    "Historical Analysis": {
        "History": 0.40,
        "Peers": 0.30,
        "Macro": 0.20,
        "Events": 0.10,
    },
    "Investment Evaluation": {
        "Business": 0.25,
        "Financial": 0.20,
        "Valuation": 0.20,
        "History": 0.15,
        "Macro": 0.10,
        "Portfolio": 0.10,
    },
    "Peer Comparison": {
        "Peers": 0.45,
        "Financial": 0.25,
        "Valuation": 0.20,
        "History": 0.10,
    },
    "Macro Impact": {
        "Macro": 0.45,
        "Events": 0.20,
        "Sector": 0.20,
        "History": 0.15,
    },
    "Portfolio Decision": {
        "Portfolio": 0.40,
        "Risk": 0.25,
        "Macro": 0.15,
        "Valuation": 0.10,
        "History": 0.10,
    },
    "Educational": {
        "Concept": 0.70,
        "Example": 0.30,
    },
    "Valuation Assessment": {
        "Valuation": 0.40,
        "History": 0.30,
        "Peers": 0.20,
        "Macro": 0.10,
    },
}


def prioritise_context(
    primary_objective: str | None,
    *,
    comparison_lenses: list[str] | None = None,
    portfolio_required: bool = False,
    events: list[str] | None = None,
) -> dict[str, Any]:
    obj = primary_objective or ""
    weights = dict(_TEMPLATES.get(obj) or {"Core": 0.6, "Macro": 0.2, "History": 0.2})
    # Soft adjust
    if portfolio_required and "Portfolio" not in weights:
        weights["Portfolio"] = 0.1
        total = sum(weights.values())
        weights = {k: round(v / total, 4) for k, v in weights.items()}
    if events and "Events" not in weights:
        weights["Events"] = 0.08
        total = sum(weights.values())
        weights = {k: round(v / total, 4) for k, v in weights.items()}

    # Normalize
    total = sum(weights.values()) or 1.0
    weights = {k: round(v / total, 4) for k, v in weights.items()}
    drift = round(1.0 - sum(weights.values()), 4)
    if weights:
        top = max(weights, key=weights.get)
        weights[top] = round(weights[top] + drift, 4)

    ranked = sorted(weights.items(), key=lambda kv: -kv[1])
    return {
        "context_importance": weights,
        "priority_order": [k for k, _ in ranked],
        "map_version": "cie-v1",
    }
