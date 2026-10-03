"""FKB pillar weights for Business Quality (FIRE-06) — knowledge only, configurable."""

from __future__ import annotations

from typing import Any

# Weights must sum to 1.0 for the default profile. Consumers renormalize if pillars missing.
PILLAR_WEIGHTS: dict[str, dict[str, Any]] = {
    "growth_quality": {
        "id": "growth_quality",
        "pillar": "Growth Quality",
        "weight": 0.18,
        "description": "Relative weight of growth quality in overall business quality.",
        "configurable": True,
        "performs_analysis": False,
    },
    "profitability_quality": {
        "id": "profitability_quality",
        "pillar": "Profitability Quality",
        "weight": 0.18,
        "description": "Relative weight of profitability quality in overall business quality.",
        "configurable": True,
        "performs_analysis": False,
    },
    "cash_flow_quality": {
        "id": "cash_flow_quality",
        "pillar": "Cash Flow Quality",
        "weight": 0.18,
        "description": "Relative weight of cash flow quality in overall business quality.",
        "configurable": True,
        "performs_analysis": False,
    },
    "balance_sheet_quality": {
        "id": "balance_sheet_quality",
        "pillar": "Balance Sheet Quality",
        "weight": 0.14,
        "description": "Relative weight of balance sheet quality in overall business quality.",
        "configurable": True,
        "performs_analysis": False,
    },
    "capital_allocation_quality": {
        "id": "capital_allocation_quality",
        "pillar": "Capital Allocation Quality",
        "weight": 0.12,
        "description": "Relative weight of capital allocation quality in overall business quality.",
        "configurable": True,
        "performs_analysis": False,
    },
    "management_execution": {
        "id": "management_execution",
        "pillar": "Management Execution",
        "weight": 0.12,
        "description": "Relative weight of FIRE-05 management execution in overall business quality.",
        "configurable": True,
        "performs_analysis": False,
    },
    "business_model_stability": {
        "id": "business_model_stability",
        "pillar": "Business Model Stability",
        "weight": 0.08,
        "description": "Relative weight of disclosed business-model diversification / stability.",
        "configurable": True,
        "performs_analysis": False,
    },
}


def all_quality_weights() -> list[dict[str, Any]]:
    return [dict(PILLAR_WEIGHTS[k]) for k in sorted(PILLAR_WEIGHTS)]


def get_quality_weight(key: str) -> dict[str, Any] | None:
    k = key.strip().lower().replace(" ", "_").replace("-", "_")
    row = PILLAR_WEIGHTS.get(k)
    return dict(row) if row else None


def weight_map() -> dict[str, float]:
    return {k: float(v["weight"]) for k, v in PILLAR_WEIGHTS.items()}
