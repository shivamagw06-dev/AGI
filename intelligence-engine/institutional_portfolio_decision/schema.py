"""CIO-01 — Institutional Portfolio Decision System constants."""

from __future__ import annotations

CIO_WORKSTREAM_ID = "CIO-01"
CIO_PRODUCT = "Institutional Portfolio Decision System"
CIO_VERSION = "cio-01-v1.0.0"
CIO_SPEC = "docs/AGI_CIO_01_PORTFOLIO_DECISION.md"
CIO_ROLE = "deterministic_portfolio_decision"
DECISION_ENGINE_VERSION = "cio-01-decision-engine-v1"
VALIDATOR_VERSION = "cio-01-validator-v1"
CALIBRATION_VERSION = "cio-01-calibration-v1"
DEFAULT_PORTFOLIO_ID = "agi-core-equity"

PORTFOLIO_RECOMMENDATIONS = (
    "Maintain Allocation",
    "Increase Financials",
    "Reduce Technology",
    "Increase Cash",
    "Reduce Concentration",
    "Increase Diversification",
    "Review Portfolio",
    "No Action Required",
)

CONVICTIONS = ("LOW", "MEDIUM", "HIGH")

INVESTMENT_POSTURES = (
    "Defensive",
    "Neutral",
    "Constructive",
    "Aggressive",
    "Review",
)

LINEAGE_CHAIN = (
    "Portfolio",
    "Holding",
    "Portfolio Risk",
    "Policy Constraint",
    "Company Decision",
    "Reason",
    "Evidence",
)
