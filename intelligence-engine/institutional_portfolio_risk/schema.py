"""PRE-01 — Institutional Portfolio Risk Engine constants."""

from __future__ import annotations

PRE_WORKSTREAM_ID = "PRE-01"
PRE_PRODUCT = "Institutional Portfolio Risk Engine"
PRE_VERSION = "pre-01-v1.0.0"
PRE_SPEC = "docs/AGI_PRE_01_PORTFOLIO_RISK.md"
PRE_ROLE = "deterministic_portfolio_risk"
RISK_ENGINE_VERSION = "pre-01-risk-engine-v1"
VALIDATOR_VERSION = "pre-01-validator-v1"
DEFAULT_PORTFOLIO_ID = "agi-core-equity"

OVERALL_RISK_LEVELS = ("Low", "Moderate", "High", "Critical")

LINEAGE_CHAIN = (
    "Portfolio",
    "Holding",
    "Risk Dimension",
    "Company Decision",
    "Reason",
    "Evidence",
)

STRESS_SCENARIOS = (
    "rbi_plus_50bps",
    "rbi_minus_50bps",
    "market_minus_10",
    "market_minus_20",
    "oil_shock",
    "inr_shock",
    "banking_stress",
)
