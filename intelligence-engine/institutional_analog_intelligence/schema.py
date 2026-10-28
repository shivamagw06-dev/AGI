"""IMAI — Institutional Memory & Analog Intelligence schemas."""

from __future__ import annotations

from typing import Any

IMAI_VERSION = "institutional-analog-intelligence-v1.0.0"
PROGRAMME = "AGIB v3.6 – Phase 2 Institutional Intelligence · Sprint 2.2 Memory & Analogs"
MODULE_CODE = "IMAI"

# Distinct from ILM (Institutional Learning & Memory — mistakes/forecasts).
# IMAI answers: "Have we seen this before?"
DISTINCT_FROM_ILM = True

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "planner": True,
    "reasoning_frozen": True,
    "no_new_intelligence_domains": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_analog_generation": True,
    "never_fabricate_analogues": True,
    "point_in_time_integrity": True,
    "augments_not_replaces_reasoning": True,
    "ilm_untouched": True,
}

MEMORY_TYPES: tuple[str, ...] = (
    "historical_analog",
    "previous_earnings",
    "previous_guidance",
    "previous_capital_allocation",
    "previous_management_commentary",
    "previous_policy_event",
    "previous_rate_cycle",
    "previous_inflation_cycle",
    "commodity_shock",
    "currency_shock",
    "sector_cycle",
    "market_panic",
    "recovery",
    "bull_market",
    "bear_market",
    "credit_cycle",
    "liquidity_cycle",
    "corporate_event_analog",
    "government_decision_analog",
)

REGIMES: tuple[str, ...] = (
    "high_inflation",
    "low_inflation",
    "high_rates",
    "low_rates",
    "liquidity_expansion",
    "liquidity_tightening",
    "commodity_supercycle",
    "demand_slowdown",
    "export_boom",
    "import_shock",
    "pandemic",
    "recovery",
    "election_cycle",
    "fiscal_expansion",
    "rate_cutting_cycle",
    "rate_hiking_cycle",
    "oil_spike",
    "oil_collapse",
    "fx_depreciation",
    "credit_stress",
    "bull_market",
    "bear_market",
)

# Similarity feature weights (sum ≈ 1.0)
SIMILARITY_WEIGHTS: dict[str, float] = {
    "industry": 0.14,
    "sector": 0.10,
    "macro_regime": 0.14,
    "policy_regime": 0.10,
    "commodity_exposure": 0.10,
    "financial_profile": 0.08,
    "valuation_profile": 0.06,
    "corporate_event_type": 0.08,
    "risk_profile": 0.06,
    "historical_behaviour": 0.06,
    "time_distance": 0.04,
    "evidence_quality": 0.04,
}
