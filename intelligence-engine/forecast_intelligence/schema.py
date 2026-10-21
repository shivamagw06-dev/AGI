"""Forecast Intelligence Engine (FIE) V1 — schema constants."""

from __future__ import annotations

FIE_VERSION = "1.0.0"
PROGRAMME = "AGIB_FORECAST_INTELLIGENCE_ENGINE"
PROGRAMME_SHORT = "FIE"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
PRIMARY_QUESTION = "What future paths are plausible?"
PRIMARY_QUESTION_ALT = "What is most likely to happen next?"

PIPELINE = [
    "Market Data",
    "Macro Data",
    "FIL",
    "FDI",
    "MII",
    "ACI",
    "EIL",
    "PIL",
    "CIG",
    "FORECAST INTELLIGENCE ENGINE",
    "Institutional Analysts",
    "Investment Committee",
    "Portfolio Intelligence",
    "CIO",
    "Research Writer",
    "ACS",
    "IRS",
    "Production",
]

SCENARIO_NAMES = ("bull", "base", "bear", "stress", "recovery")

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
    "portfolio_intelligence",
    "causal_intelligence",
    "institutional_analysts",
    "investment_committee",
    "cio",
    "research_writer",
    "certification",
    "regression",
    "institutional_stack",
)
