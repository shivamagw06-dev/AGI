"""AGIB v3.4 Track A — Intent Resolution Layer schemas."""

from __future__ import annotations

from typing import Any

IRL_VERSION = "intent-resolution-v1.2.0"
PROGRAMME = "AGIB v3.4 – Institutional Answer Excellence · Track A Ask Pipeline 2.0"
MODULE_CODE = "IRL"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "evidence_contracts_module": True,
    "no_new_intelligence_domains": True,
    "soft_wire_only": True,
    "reasoning_frozen": True,
}

# Track A taxonomy (canonical intents)
INTENTS_V2: tuple[str, ...] = (
    "Explain",
    "Compare",
    "Analyse",
    "Valuation",
    "Portfolio",
    "Education",
    "HistoricalReplay",
    "Risk",
    "Accounting",
    "Industry",
    "Macro",
    "Government",
    "CorporateEvents",
    "Documents",
    "CrossDomain",
    "CompanyOverview",
    "FinancialAnalysis",
    "Earnings",
    "MarketMovement",
    "Ownership",
    "Screening",
    "Forecasting",
    "Catalyst",
    "HistoricalChange",
    "Unknown",
)

# Map v2 intent → existing ask_pipeline KF selection key
INTENT_TO_LEGACY: dict[str, str] = {
    "Explain": "Education",
    "Compare": "Comparison",
    "Analyse": "Research",
    "Valuation": "Valuation",
    "Portfolio": "Portfolio",
    "Education": "Education",
    "HistoricalReplay": "Replay",
    "Risk": "Risk",
    "Accounting": "Accounting",
    "Industry": "Industry",
    "Macro": "Macro",
    "Government": "Government",
    "CorporateEvents": "Research",
    "Documents": "Research",
    "CrossDomain": "Research",
    "CompanyOverview": "Research",
    "FinancialAnalysis": "Research",
    "Earnings": "Research",
    "MarketMovement": "Research",
    "Ownership": "Research",
    "Screening": "Research",
    "Forecasting": "Research",
    "Catalyst": "Research",
    "HistoricalChange": "Historical",
    "Unknown": "Unknown",
}

# Map v2 intent → governance question_type (overrides classify_question)
INTENT_TO_QUESTION_TYPE_V2: dict[str, str] = {
    "Explain": "education",
    "Compare": "comparison",
    "Analyse": "business_quality",
    "Valuation": "valuation",
    "Portfolio": "portfolio",
    "Education": "education",
    "HistoricalReplay": "education",  # process / evidence-availability path — no live valuation
    "Risk": "risk",
    "Accounting": "financial_quality",
    "Industry": "sector",
    "Macro": "macro",
    "Government": "macro",
    "CorporateEvents": "business_quality",
    "Documents": "education",
    "CrossDomain": "macro",
    "CompanyOverview": "business_quality",
    "FinancialAnalysis": "financial_quality",
    "Earnings": "business_quality",
    "MarketMovement": "business_quality",
    "Ownership": "business_quality",
    "Screening": "comparison",
    "Forecasting": "business_quality",
    "Catalyst": "business_quality",
    "HistoricalChange": "business_quality",
    "Unknown": "education",  # safer than default valuation
}

# Minimum confidence to bind a company entity (else Concept Mode)
ENTITY_BIND_THRESHOLD = 0.75
