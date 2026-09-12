"""Macro lab — oil/rates/inflation/currency and geopolitical shocks."""

from __future__ import annotations

from typing import Any

from simulation_lab.schema import MACRO_SHOCKS

SHOCK_IMPACT = {
    "oil_plus_20": {"shock": -0.04, "channels": ["input_costs", "discretionary_demand"], "beneficiaries": ["energy"]},
    "oil_minus_20": {"shock": 0.03, "channels": ["margin_relief", "freight"], "beneficiaries": ["staples", "transport"]},
    "rates_plus_100bps": {"shock": -0.02, "channels": ["nim", "duration", "credit_cost"], "beneficiaries": ["short_duration_banks"]},
    "rates_minus_100bps": {"shock": 0.025, "channels": ["nim_compression_then_volume", "valuation"], "beneficiaries": ["growth", "duration"]},
    "inflation_shock": {"shock": -0.05, "channels": ["real_income", "working_capital"], "beneficiaries": ["pricing_power"]},
    "gdp_slowdown": {"shock": -0.06, "channels": ["volume", "credit_demand"], "beneficiaries": ["defensive_quality"]},
    "currency_shock": {"shock": -0.03, "channels": ["import_costs", "fii_flows"], "beneficiaries": ["exporters"]},
    "election": {"shock": -0.015, "channels": ["policy_uncertainty"], "beneficiaries": ["domestics"]},
    "war": {"shock": -0.09, "channels": ["risk_premia", "supply_chain"], "beneficiaries": ["safe_haven_cash"]},
    "supply_chain_disruption": {"shock": -0.045, "channels": ["inventory", "margins"], "beneficiaries": ["vertical_integrators"]},
    "credit_crisis": {"shock": -0.12, "channels": ["liquidity", "credit_spreads"], "beneficiaries": ["fortress_balance_sheets"]},
}


def resolve_macro_shock(assumptions: dict[str, Any]) -> dict[str, Any]:
    shock_id = str(assumptions.get("macro_shock") or assumptions.get("shock") or "")
    if shock_id not in MACRO_SHOCKS:
        # Infer from family keywords
        for key in MACRO_SHOCKS:
            if key in str(assumptions):
                shock_id = key
                break
    if shock_id not in SHOCK_IMPACT:
        return {
            "active": False,
            "shock_id": None,
            "shock": 0.0,
            "channels": [],
            "available": list(MACRO_SHOCKS),
        }
    meta = SHOCK_IMPACT[shock_id]
    return {
        "active": True,
        "shock_id": shock_id,
        "shock": meta["shock"],
        "channels": meta["channels"],
        "beneficiaries": meta["beneficiaries"],
        "assumptions_recorded": True,
        "rule": "Macro shocks shift distributional mass — never a single point forecast",
    }
