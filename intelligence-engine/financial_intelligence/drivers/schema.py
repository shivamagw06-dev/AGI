"""FIRE-02 contracts — relationship & driver analysis."""

from __future__ import annotations

WORKSTREAM_ID = "FIRE-02"
PROGRAMME = "AGIB_FINANCIAL_INTELLIGENCE_REASONING_ENGINE"
SUBSYSTEM = "financial_relationship_driver_analysis"
VERSION = "fire-02-v1.0.0"
PHASE = "phase_2"
SPEC = "docs/FIRE_02_FINANCIAL_RELATIONSHIP_DRIVER_ANALYSIS.md"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "evidence_backed_relationships_only_no_buy_sell"

# Severity for relationships (spec uses Medium/High etc.)
SEV_LOW = "Low"
SEV_MEDIUM = "Medium"
SEV_HIGH = "High"
SEV_INFO = "Info"

CATEGORIES = (
    "Revenue Drivers",
    "Margin Drivers",
    "Cash Quality",
    "Cash Flow Drivers",
    "Working Capital",
    "Working Capital Drivers",
    "Balance Sheet",
    "Balance Sheet Drivers",
    "Capital Allocation",
    "Capital Allocation Drivers",
    "Return Drivers",
    "Profitability Drivers",
    "Financial Relationships Summary",
)

DRIVER_SECTION = "financial_drivers"

DRIVER_SUBSECTIONS = (
    "revenue_drivers",
    "margin_drivers",
    "cash_flow_drivers",
    "working_capital_drivers",
    "balance_sheet_drivers",
    "capital_allocation_drivers",
    "return_drivers",
    "financial_relationships_summary",
)

# Extended metric set for cross-statement analysis
DRIVER_METRICS = (
    "revenue",
    "gross_profit",
    "cogs",
    "ebitda",
    "ebit",
    "net_income",
    "gross_margin",
    "operating_margin",
    "ebitda_margin",
    "net_margin",
    "operating_cash_flow",
    "free_cash_flow",
    "capex",
    "working_capital",
    "receivables",
    "inventory",
    "payables",
    "cash",
    "total_debt",
    "net_debt",
    "total_equity",
    "interest_coverage",
    "debt_to_equity",
    "roe",
    "roce",
    "roic",
    "asset_turnover",
    "dividends",
    "share_buybacks",
    "eps_basic",
)
