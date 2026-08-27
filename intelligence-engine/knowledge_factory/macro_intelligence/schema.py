"""Institutional Macro Intelligence schemas — KF enrichment only.

Phases 1–7, Historical Depth, and Sector Intelligence remain untouched.
"""

from __future__ import annotations

from typing import Any

IMI_VERSION = "institutional-macro-intelligence-v1.0.0"
IMI_SCHEMA_VERSION = "imi-schema-v1.0.0"

MACRO_UNIVERSE: tuple[str, ...] = (
    "interest_rates",
    "inflation",
    "gdp",
    "pmi",
    "industrial_production",
    "credit_growth",
    "liquidity",
    "money_supply",
    "yield_curve",
    "government_bond_yields",
    "corporate_bond_spreads",
    "oil",
    "natural_gas",
    "coal",
    "electricity",
    "usd",
    "eur",
    "jpy",
    "usd_inr",
    "dxy",
    "gold",
    "silver",
    "copper",
    "steel",
    "agriculture",
    "trade_balance",
    "current_account",
    "fiscal_deficit",
    "government_spending",
    "consumer_confidence",
    "business_confidence",
    "housing",
    "employment",
    "unemployment",
    "manufacturing",
    "services",
    "global_growth",
    "china_growth",
    "us_growth",
    "europe_growth",
)

REGIME_LABELS: tuple[str, ...] = (
    "expansion",
    "peak",
    "contraction",
    "recovery",
    "high_inflation",
    "low_inflation",
    "high_rates",
    "low_rates",
    "yield_curve_inversion",
    "credit_expansion",
    "credit_contraction",
    "liquidity_expansion",
    "liquidity_tightening",
    "commodity_boom",
    "commodity_bust",
    "risk_on",
    "risk_off",
)


def macro_envelope(macro_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "imi_schema_version": IMI_SCHEMA_VERSION,
        "imi_version": IMI_VERSION,
        "macro_id": macro_id,
        **payload,
    }
