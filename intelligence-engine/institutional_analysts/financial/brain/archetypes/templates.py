"""Financial archetypes — pattern recognition templates."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of

ARCHETYPES: list[dict[str, Any]] = [
    {
        "id": "high_quality_compounder",
        "name": "High Quality Compounder",
        "pattern": ["High ROIC", "Strong cash conversion", "Stable/improving margins", "Disciplined allocation"],
        "signals": ("roic", "cash conversion", "margin", "improv", "disciplin", "return"),
        "confidence_bias": 0.06,
    },
    {
        "id": "cash_machine",
        "name": "Cash Machine",
        "pattern": ["High FCF", "Low working-capital drag", "Earnings convert to cash"],
        "signals": ("fcf", "cash conversion", "operating cash", "working capital"),
        "confidence_bias": 0.05,
    },
    {
        "id": "negative_wc_compounder",
        "name": "Negative Working Capital Compounder",
        "pattern": ["Negative/low WC", "Cash leads earnings", "Scalable reinvestment"],
        "signals": ("working capital", "cash conversion", "asset-light", "negative"),
        "confidence_bias": 0.04,
    },
    {
        "id": "asset_heavy_cyclical",
        "name": "Asset Heavy Cyclical",
        "pattern": ["High capex", "Cycle-sensitive returns", "Capacity timing critical"],
        "signals": ("capex", "cyclical", "capacity", "asset", "commodity"),
        "confidence_bias": -0.02,
    },
    {
        "id": "turnaround",
        "name": "Turnaround",
        "pattern": ["Margins recovering", "Cash still fragile", "Leverage watch"],
        "signals": ("turnaround", "recover", "restructur", "improv", "stress"),
        "confidence_bias": -0.03,
    },
    {
        "id": "capital_destroyer",
        "name": "Capital Destroyer",
        "pattern": ["Poor incremental returns", "Cash burn / leverage", "Allocation failure"],
        "signals": ("cash burn", "destroy", "stress", "high leverage", "loss"),
        "confidence_bias": -0.08,
    },
    {
        "id": "value_trap",
        "name": "Value Trap",
        "pattern": ["Apparent cheapness elsewhere", "Stagnant returns", "Weak cash"],
        "signals": ("stagnant", "weak cash", "low return", "trap"),
        "confidence_bias": -0.05,
    },
    {
        "id": "financially_engineered_growth",
        "name": "Financially Engineered Growth",
        "pattern": ["Growth via leverage/accruals", "Cash lags earnings", "Quality flags"],
        "signals": ("leverage", "accrual", "aggress", "mismatch", "engineered"),
        "confidence_bias": -0.07,
    },
    {
        "id": "compounder",
        "name": "Compounder",
        "pattern": ["Multi-year return persistence", "Self-funded growth"],
        "signals": ("compound", "roic", "cash", "stable", "reinvest"),
        "confidence_bias": 0.04,
    },
]


def match_archetype(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    blob = blob_of(
        evidence.get("narrative"),
        evidence.get("trend"),
        evidence.get("financial_quality"),
        evidence.get("cash_flow"),
        evidence.get("debt"),
        evidence.get("working_capital"),
        (frameworks.get("returns") or {}).get("assessment"),
        (frameworks.get("cash_flow") or {}).get("assessment"),
        (frameworks.get("earnings_quality") or {}).get("assessment"),
    )
    scored = sorted(
        ((sum(1 for s in a.get("signals") or () if s in blob), a) for a in ARCHETYPES),
        key=lambda x: x[0],
        reverse=True,
    )
    primary = scored[0][1] if scored and scored[0][0] > 0 else ARCHETYPES[0]
    return {
        "primary": {
            "id": primary["id"],
            "name": primary["name"],
            "pattern": list(primary.get("pattern") or []),
            "confidence_bias": float(primary.get("confidence_bias") or 0),
            "match_score": scored[0][0] if scored else 0,
        },
        "template_reasoning": (
            f"Financial archetype: {primary['name']}. Pattern — "
            + "; ".join(primary.get("pattern") or [])
            + "."
        ),
    }
