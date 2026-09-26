"""Append-only simulation history + seeded institutional scenario templates."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from simulation_lab.schema import (
    COMPANY_SIMULATIONS,
    HISTORICAL_REPLAYS,
    MACRO_SHOCKS,
    PORTFOLIO_SIMULATIONS,
)

# Seeded scenario catalogue — evidence-backed assumptions, not price targets.
SCENARIO_CATALOGUE: list[dict[str, Any]] = [
    {
        "id": "rebalance_hdfc_plus",
        "family": "portfolio_rebalance",
        "label": "Increase HDFCBANK weight +150 bps",
        "ticker": "HDFCBANK",
        "portfolio_id": "agib_core_india",
        "objective": "Test concentration vs franchise quality when overweighting HDFCBANK",
        "assumptions": {
            "weight_delta_bps": 150,
            "funding": "trim_cash_and_peers",
            "horizon_months": 12,
            "evidence": ["FIL liability franchise", "ILM timing lessons on NIM", "FIE base case"],
        },
        "supported_simulations": ["portfolio_rebalance", "weight_increase", "buy_candidate"],
    },
    {
        "id": "trim_tcs_growth",
        "family": "weight_reduction",
        "label": "Trim TCS −100 bps toward quality cash sleeve",
        "ticker": "TCS",
        "portfolio_id": "agib_core_india",
        "objective": "Test opportunity cost of reducing IT growth exposure",
        "assumptions": {
            "weight_delta_bps": -100,
            "redeploy": "quality_cash",
            "horizon_months": 12,
            "evidence": ["PIL peer IT margins", "FIE demand uncertainty"],
        },
        "supported_simulations": ["weight_reduction", "sell_candidate", "growth_strategy"],
    },
    {
        "id": "oil_plus_20_nestle",
        "family": "macro",
        "label": "Oil +20% shock on Nestlé India / staples sleeve",
        "ticker": "NESTLEIND",
        "portfolio_id": "agib_core_india",
        "objective": "Estimate margin and demand path under oil shock without deterministic outcomes",
        "assumptions": {
            "macro_shock": "oil_plus_20",
            "pass_through": 0.35,
            "demand_elasticity": -0.2,
            "evidence": ["CIG oil→input cost chain", "IKG commodity links"],
        },
        "supported_simulations": ["oil_plus_20", "margins", "stress"],
    },
    {
        "id": "rates_plus_100_banks",
        "family": "macro",
        "label": "Rates +100 bps — bank sleeve NIM / credit path",
        "ticker": "HDFCBANK",
        "portfolio_id": "agib_core_india",
        "objective": "Simulate NIM and credit cost paths under a +100 bps policy shock",
        "assumptions": {
            "macro_shock": "rates_plus_100bps",
            "nim_sensitivity": 0.12,
            "credit_cost_uplift": 0.08,
            "evidence": ["CIG repo→NIM", "MII guidance credibility", "ILM NIM timing lesson"],
        },
        "supported_simulations": ["rates_plus_100bps", "stress", "portfolio_rebalance"],
    },
    {
        "id": "quality_vs_value",
        "family": "strategy",
        "label": "High Quality vs Deep Value sleeve comparison",
        "ticker": "HDFCBANK",
        "portfolio_id": "agib_core_india",
        "objective": "Compare concentrated quality vs diversified deep value under FIE distributions",
        "assumptions": {
            "strategy_a": "high_quality",
            "strategy_b": "deep_value",
            "horizon_months": 24,
            "evidence": ["ACI quality scores", "PIL peer ranks", "FIE scenario mass"],
        },
        "supported_simulations": ["quality_strategy", "value_strategy", "strategy_compare"],
    },
    {
        "id": "replay_covid_core",
        "family": "replay",
        "label": "Replay COVID / 2020 lockdowns on core India book",
        "ticker": "HDFCBANK",
        "portfolio_id": "agib_core_india",
        "objective": "Estimate portfolio behaviour and decision quality under COVID analogue",
        "assumptions": {
            "replay": "covid",
            "also": "lockdowns_2020",
            "evidence": ["ILM historical lessons", "FIL crisis disclosures", "CIG shock chains"],
        },
        "supported_simulations": ["covid", "lockdowns_2020", "stress"],
    },
]

_RUN_HISTORY: list[dict[str, Any]] = []


def list_scenarios() -> list[dict[str, Any]]:
    return deepcopy(SCENARIO_CATALOGUE)


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    for s in SCENARIO_CATALOGUE:
        if s["id"] == scenario_id:
            return deepcopy(s)
    return None


def catalogue_meta() -> dict[str, Any]:
    return {
        "portfolio_simulations": list(PORTFOLIO_SIMULATIONS),
        "macro_shocks": list(MACRO_SHOCKS),
        "company_simulations": list(COMPANY_SIMULATIONS),
        "historical_replays": list(HISTORICAL_REPLAYS),
        "scenario_count": len(SCENARIO_CATALOGUE),
        "scenario_ids": [s["id"] for s in SCENARIO_CATALOGUE],
    }


def append_run(record: dict[str, Any]) -> dict[str, Any]:
    """Append-only simulation history — never overwrite prior runs."""
    row = deepcopy(record)
    row["run_index"] = len(_RUN_HISTORY) + 1
    row["append_only"] = True
    row["overwritten"] = False
    _RUN_HISTORY.append(row)
    return deepcopy(row)


def list_history(*, limit: int = 50) -> list[dict[str, Any]]:
    return deepcopy(_RUN_HISTORY[-max(1, min(limit, 200)) :])


def clear_history_for_tests() -> None:
    _RUN_HISTORY.clear()
