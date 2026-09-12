"""Explicit lifecycle states for Hedge Fund strategy research."""

from __future__ import annotations

from typing import Any

QUALIFICATION_PIPELINE = [
    "signal_definition",
    "data_requirements",
    "research_backtest",
    "point_in_time_validation",
    "transaction_costs",
    "liquidity_and_capacity",
    "risk_analysis",
    "out_of_sample_test",
    "production_qualification",
    "live_monitoring",
]

STRATEGY_QUALIFICATION: dict[str, dict[str, Any]] = {
    "long_short_equity": {"status": "candidate", "label": "Candidate", "operational_scope": "research_scanners"},
    "equity_market_neutral": {"status": "candidate", "label": "Candidate", "operational_scope": "qualification_framework"},
    "statistical_arbitrage": {"status": "candidate", "label": "Candidate", "operational_scope": "calculator_and_research"},
    "global_macro": {"status": "framework", "label": "Framework", "operational_scope": "methodology_only"},
    "merger_arbitrage": {"status": "framework", "label": "Framework", "operational_scope": "methodology_only"},
    "convertible_arbitrage": {"status": "framework", "label": "Framework", "operational_scope": "methodology_only"},
    "cta_trend": {"status": "framework", "label": "Framework", "operational_scope": "methodology_only"},
    "distressed": {"status": "candidate", "label": "Candidate", "operational_scope": "research_scanner"},
}


def qualification_for(strategy_id: str) -> dict[str, Any]:
    from reliability_registry import component

    reliability = component(strategy_id)
    return {
        "status": reliability["lifecycle"],
        "label": reliability["lifecycle_label"],
        "operational_scope": reliability["allowed_use"].lower().replace(" ", "_"),
        "pipeline": list(QUALIFICATION_PIPELINE),
        "production_validated": reliability["lifecycle"] == "production",
        "reliability": reliability,
    }
