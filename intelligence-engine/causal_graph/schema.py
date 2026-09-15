"""Causal Intelligence Graph (CIG) V1 — schema constants."""

from __future__ import annotations

CIG_VERSION = "1.0.0"
PROGRAMME = "AGIB_CAUSAL_INTELLIGENCE_GRAPH"
PROGRAMME_SHORT = "CIG"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
PRIMARY_QUESTION = "Why did this happen?"

PIPELINE = [
    "Live Market Data",
    "Macro Data",
    "Official Filings",
    "FIL",
    "FDI",
    "MII",
    "ACI",
    "EIL",
    "PIL",
    "CAUSAL INTELLIGENCE GRAPH",
    "Institutional Analysts",
    "Investment Committee",
    "Portfolio Intelligence",
    "CIO",
    "Research Writer",
    "ACS",
    "IRS",
    "Production",
]

NODE_TYPES = (
    "economy",
    "country",
    "central_bank",
    "interest_rate",
    "bond_yield",
    "inflation",
    "currency",
    "commodity",
    "sector",
    "company",
    "product",
    "customer",
    "supplier",
    "management",
    "financial_metric",
    "valuation_multiple",
    "risk_factor",
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
    "portfolio_intelligence",
    "institutional_analysts",
    "investment_committee",
    "cio",
    "research_writer",
    "certification",
    "regression",
    "institutional_stack",
)
