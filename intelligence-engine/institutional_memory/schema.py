"""Institutional Learning & Memory Engine (ILM) V1 — schema constants."""

from __future__ import annotations

ILM_VERSION = "1.0.0"
PROGRAMME = "AGIB_INSTITUTIONAL_LEARNING_MEMORY"
PROGRAMME_SHORT = "ILM"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
PRIMARY_QUESTION = "What has AGIB learned over time?"
PRIMARY_QUESTION_ALT = "What have we learned?"

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
    "INSTITUTIONAL LEARNING & MEMORY",
    "Institutional Analysts",
    "Investment Committee",
    "Portfolio Intelligence",
    "CIO",
    "Research Writer",
    "ACS",
    "IRS",
    "Production",
]

MISTAKE_TYPES = (
    "evidence_error",
    "reasoning_error",
    "probability_error",
    "timing_error",
    "macro_error",
    "management_error",
    "accounting_error",
    "portfolio_error",
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
    "forecast_intelligence",
    "knowledge_graph",
    "portfolio_intelligence",
    "institutional_analysts",
    "investment_committee",
    "cio",
    "research_writer",
    "certification",
    "regression",
    "institutional_stack",
)
