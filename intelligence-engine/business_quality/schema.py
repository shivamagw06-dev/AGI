"""FIRE-06 — Business Quality Engine contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FIRE-06"
PROGRAMME = "AGIB_FINANCIAL_INTELLIGENCE_REASONING_ENGINE"
SUBSYSTEM = "business_quality_engine"
VERSION = "fire-06-v1.0.0"
PHASE = "phase_6"
SPEC = "docs/FIRE_06_BUSINESS_QUALITY_ENGINE.md"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "business_quality_synthesis_only_no_buy_sell"

CONF_HIGH = "High"
CONF_MEDIUM = "Medium"
CONF_LOW = "Low"

PILLAR_GROWTH = "growth_quality"
PILLAR_PROFIT = "profitability_quality"
PILLAR_CASH = "cash_flow_quality"
PILLAR_BALANCE = "balance_sheet_quality"
PILLAR_CAPITAL = "capital_allocation_quality"
PILLAR_EXECUTION = "management_execution"
PILLAR_MODEL = "business_model_stability"

PILLARS = (
    PILLAR_GROWTH,
    PILLAR_PROFIT,
    PILLAR_CASH,
    PILLAR_BALANCE,
    PILLAR_CAPITAL,
    PILLAR_EXECUTION,
    PILLAR_MODEL,
)

PILLAR_TITLES = {
    PILLAR_GROWTH: "Growth Quality",
    PILLAR_PROFIT: "Profitability Quality",
    PILLAR_CASH: "Cash Flow Quality",
    PILLAR_BALANCE: "Balance Sheet Quality",
    PILLAR_CAPITAL: "Capital Allocation Quality",
    PILLAR_EXECUTION: "Management Execution",
    PILLAR_MODEL: "Business Model Stability",
}

REPORT_SECTIONS = (
    "executive_summary",
    "overall_quality",
    "growth_quality",
    "profitability_quality",
    "cash_quality",
    "balance_sheet_quality",
    "capital_allocation",
    "management_execution",
    "business_model",
    "strengths",
    "weaknesses",
    "confidence",
    "evidence_references",
)

QUALITY_METRICS = (
    "revenue",
    "gross_margin",
    "operating_margin",
    "ebitda_margin",
    "net_margin",
    "roe",
    "roce",
    "roic",
    "operating_cash_flow",
    "free_cash_flow",
    "working_capital",
    "total_debt",
    "net_debt",
    "interest_coverage",
    "cash",
    "capex",
    "dividends",
    "share_buybacks",
    "net_income",
)

# Forbidden marketing / investment language in narratives
FORBIDDEN_PHRASES = (
    "excellent company",
    "poor company",
    "great investment",
    "bad investment",
    "buy",
    "sell",
    "undervalued",
    "overvalued",
)
