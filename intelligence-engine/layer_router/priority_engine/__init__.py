"""Importance scores per layer by research objective."""

from __future__ import annotations

from typing import Any

# 0–100 importance
_BY_OBJECTIVE: dict[str, dict[str, int]] = {
    "Investment Evaluation": {
        "FIL": 100,
        "FDI": 70,
        "EIL": 95,
        "ACI": 75,
        "PIL": 90,
        "CIG": 60,
        "IKG": 65,
        "FIE": 80,
        "ILM": 55,
        "Business": 100,
        "Financial": 95,
        "Valuation": 95,
        "Risk": 85,
        "Portfolio": 80,
        "Committee": 90,
        "IDE V2": 85,
        "CIO": 80,
        "Research Writer": 75,
        "Macro": 55,
        "MII": 35,
        "Management": 30,
        "Ownership": 15,
        "SSL": 20,
        "Sector": 40,
    },
    "Historical Analysis": {
        "FIL": 70,
        "EIL": 90,
        "PIL": 100,
        "CIG": 75,
        "FIE": 70,
        "IKG": 50,
        "ILM": 60,
        "Valuation": 95,
        "Sector": 90,
        "Macro": 80,
        "Business": 10,
        "Management": 5,
        "Portfolio": 5,
        "Ownership": 5,
        "SSL": 5,
        "MII": 5,
        "Committee": 40,
        "Research Writer": 60,
        "CIO": 35,
        "IDE V2": 30,
    },
    "Peer Comparison": {
        "FIL": 80,
        "EIL": 90,
        "PIL": 100,
        "CIG": 50,
        "Business": 90,
        "Financial": 90,
        "Valuation": 95,
        "Sector": 85,
        "Portfolio": 10,
        "Management": 15,
        "Ownership": 10,
        "SSL": 5,
        "Research Writer": 70,
        "Committee": 50,
    },
    "Educational": {
        "Research Writer": 40,
        "ILM": 30,
        "FIL": 5,
        "Business": 5,
        "Valuation": 5,
        "Portfolio": 0,
        "SSL": 0,
        "Committee": 0,
        "IDE V2": 0,
        "CIO": 0,
    },
    "Macro Impact": {
        "CIG": 100,
        "Macro": 100,
        "Sector": 85,
        "FIE": 80,
        "EIL": 70,
        "FIL": 60,
        "Risk": 75,
        "PIL": 50,
        "SSL": 40,
        "Portfolio": 30,
        "Business": 20,
        "Ownership": 5,
        "Research Writer": 70,
        "Committee": 55,
    },
    "Portfolio Decision": {
        "Portfolio": 100,
        "Risk": 95,
        "SSL": 90,
        "FIE": 80,
        "Valuation": 70,
        "PIL": 60,
        "EIL": 55,
        "FIL": 50,
        "Committee": 85,
        "IDE V2": 90,
        "CIO": 85,
        "Business": 40,
        "Ownership": 15,
        "Research Writer": 70,
    },
    "Risk Assessment": {
        "Risk": 100,
        "FIL": 80,
        "EIL": 85,
        "ACI": 70,
        "FIE": 65,
        "Macro": 75,
        "SSL": 80,
        "Portfolio": 60,
        "Business": 30,
        "Ownership": 20,
        "Research Writer": 60,
    },
    "Valuation Assessment": {
        "FIL": 85,
        "EIL": 90,
        "PIL": 95,
        "FIE": 70,
        "Valuation": 100,
        "Financial": 85,
        "CIG": 50,
        "Business": 40,
        "Portfolio": 20,
        "SSL": 10,
        "Research Writer": 65,
    },
}


def score_importance(
    primary_objective: str | None,
    *,
    required_analysts: list[str] | None = None,
) -> dict[str, Any]:
    base = dict(_BY_OBJECTIVE.get(primary_objective or "", {}))
    # Boost analysts selected by IAR
    for a in required_analysts or []:
        if a in base:
            base[a] = max(base[a], 90)
        else:
            base[a] = 85
    # Default low scores for unlisted registered layers so suppression can act
    from layer_router.schema import REGISTERED_LAYERS

    for layer in REGISTERED_LAYERS:
        base.setdefault(layer, 10 if primary_objective != "Educational" else 0)
    ranked = sorted(base.items(), key=lambda kv: -kv[1])
    return {"importance": base, "ranked": ranked, "map_version": "ilr-v1"}
