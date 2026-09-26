"""Quantified pillar interactions and propagated influence."""

from __future__ import annotations

from typing import Any

from thesis_engine.schema import PILLARS

# Directed influence: source pillar -> target pillar. Values are signed [-1, 1].
_INFLUENCE: dict[tuple[str, str], float] = {
    ("Business Quality", "Financial Quality"): 0.60,
    ("Business Quality", "Competitive Position"): 0.55,
    ("Business Quality", "Macro Alignment"): 0.20,
    ("Financial Quality", "Capital Allocation"): 0.50,
    ("Financial Quality", "Valuation"): 0.40,
    ("Competitive Position", "Valuation"): 0.35,
    ("Macro Alignment", "Valuation"): 0.25,
    ("Macro Alignment", "Portfolio Fit"): 0.30,
    ("Valuation", "Portfolio Fit"): 0.20,
    ("Capital Allocation", "Financial Quality"): 0.25,
}


def build_interaction_matrix(pillars: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {p["pillar"]: p for p in pillars}
    values: list[list[float]] = []
    edges: list[dict[str, Any]] = []
    propagated: dict[str, float] = {name: 0.0 for name in PILLARS}

    for source in PILLARS:
        row = []
        source_strength = float((by_name.get(source) or {}).get("strength") or 0.5)
        centered = 2.0 * source_strength - 1.0
        for target in PILLARS:
            weight = 1.0 if source == target else float(_INFLUENCE.get((source, target), 0.0))
            row.append(weight)
            if source != target and weight:
                contribution = round(weight * centered * 0.1, 4)
                propagated[target] += contribution
                edges.append(
                    {
                        "from": source,
                        "to": target,
                        "influence": weight,
                        "source_strength": round(source_strength, 4),
                        "conviction_effect": contribution,
                    }
                )
        values.append(row)

    for target in propagated:
        propagated[target] = round(propagated[target], 4)

    return {
        "pillars": list(PILLARS),
        "values": values,
        "edges": edges,
        "propagated_effects": propagated,
        "scale": {"min": -1.0, "max": 1.0, "meaning": "signed source-to-target influence"},
        "example_chain": "Business Quality (+0.60) → Financial Quality (+0.40) → Valuation (+0.20) → Portfolio Fit",
    }
