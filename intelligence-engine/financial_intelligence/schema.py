"""FIRE-01 — Financial Narrative & Trend Engine contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FIRE-01"
PROGRAMME = "AGIB_FINANCIAL_INTELLIGENCE_REASONING_ENGINE"
SUBSYSTEM = "financial_narrative_trend_engine"
VERSION = "fire-01-v1.0.0"
PHASE = "phase_1"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "evidence_backed_intelligence_only_no_buy_sell"
SPEC = "docs/FIRE_01_FINANCIAL_NARRATIVE_TREND_ENGINE.md"

# Report sections (ordered)
REPORT_SECTIONS = (
    "executive_summary",
    "revenue_analysis",
    "profitability",
    "margin_analysis",
    "cash_flow_quality",
    "working_capital",
    "balance_sheet_strength",
    "capital_allocation",
    "growth_quality",
    "risks",
    "key_positives",
    "key_negatives",
    "overall_financial_assessment",
)

# Trend windows
WINDOWS = ("qoq", "yoy", "y3", "y5")

# Confidence bands
CONF_HIGH = "High"
CONF_MEDIUM = "Medium"
CONF_LOW = "Low"

# Finding severities
SEV_INFO = "info"
SEV_POSITIVE = "positive"
SEV_WARNING = "warning"
SEV_NEGATIVE = "negative"

# Core trend metrics (warehouse / DME names)
TREND_METRICS = (
    "revenue",
    "operating_margin",
    "ebitda_margin",
    "net_margin",
    "roe",
    "roce",
    "total_debt",
    "cash",
    "working_capital",
    "free_cash_flow",
    "operating_cash_flow",
    "eps_basic",
    "net_income",
)

# Category mapping for findings
CATEGORY_BY_METRIC = {
    "revenue": "revenue_analysis",
    "net_income": "profitability",
    "operating_margin": "margin_analysis",
    "ebitda_margin": "margin_analysis",
    "net_margin": "margin_analysis",
    "roe": "profitability",
    "roce": "profitability",
    "total_debt": "balance_sheet_strength",
    "cash": "balance_sheet_strength",
    "working_capital": "working_capital",
    "free_cash_flow": "cash_flow_quality",
    "operating_cash_flow": "cash_flow_quality",
    "eps_basic": "growth_quality",
}

MARGIN_METRICS = frozenset({"operating_margin", "ebitda_margin", "net_margin", "gross_margin"})
