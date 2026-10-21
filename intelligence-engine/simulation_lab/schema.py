"""Institutional Simulation & Strategy Lab (SSL) V1 — schema constants."""

from __future__ import annotations

SSL_VERSION = "1.0.0"
PROGRAMME = "AGIB_SIMULATION_STRATEGY_LAB"
PROGRAMME_SHORT = "SSL"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
PRIMARY_QUESTION = "What happens if this decision is taken?"
PRIMARY_QUESTION_ALT = "What happens before we make the decision?"

PIPELINE = [
    "FIL",
    "FDI",
    "MII",
    "ACI",
    "EIL",
    "PIL",
    "CIG",
    "IKG",
    "FIE",
    "ILM",
    "SIMULATION & STRATEGY LAB",
    "Institutional Analysts",
    "Investment Committee",
    "Portfolio Intelligence",
    "CIO",
    "Research Writer",
    "ACS",
    "IRS",
    "Production",
]

PORTFOLIO_SIMULATIONS = (
    "portfolio_rebalance",
    "buy_candidate",
    "sell_candidate",
    "weight_increase",
    "weight_reduction",
    "sector_rotation",
    "country_rotation",
    "factor_rotation",
    "dividend_strategy",
    "value_strategy",
    "growth_strategy",
    "quality_strategy",
)

MACRO_SHOCKS = (
    "oil_plus_20",
    "oil_minus_20",
    "rates_plus_100bps",
    "rates_minus_100bps",
    "inflation_shock",
    "gdp_slowdown",
    "currency_shock",
    "election",
    "war",
    "supply_chain_disruption",
    "credit_crisis",
)

COMPANY_SIMULATIONS = (
    "revenue_growth",
    "margins",
    "roic",
    "cash_flow",
    "working_capital",
    "valuation_multiple",
    "capital_allocation",
    "management_change",
    "regulatory_shock",
    "acquisition",
)

HISTORICAL_REPLAYS = (
    "covid",
    "gfc",
    "taper_tantrum",
    "inflation_2022",
    "banking_crisis_2008",
    "lockdowns_2020",
)

NO_REDESIGN = (
    "engine",
    "ui",
    "provider",
    "filing_intelligence",
    "filing_diff",
    "management_intelligence",
    "accounting_intelligence",
    "evidence_intelligence",
    "peer_intelligence",
    "causal_intelligence",
    "knowledge_graph",
    "forecast_intelligence",
    "institutional_memory",
    "portfolio_intelligence",
    "institutional_analysts",
    "investment_committee",
    "cio",
    "research_writer",
    "certification",
    "regression",
    "institutional_stack",
)
