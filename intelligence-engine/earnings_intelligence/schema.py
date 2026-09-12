"""P2.1 Earnings / Financial Statements Intelligence — schema & version.

Programme workstream: P2.1 (Earnings Intelligence).
Delivers the NSE XBRL financial-statements pipeline (post-P2.3 ownership pattern).
"""

from __future__ import annotations

ENGINE_CODE = "earnings_intelligence"
ENGINE_NAME = "Financial Statements & Earnings Intelligence"
VERSION = "p2.1-v1.0.0"
WORKSTREAM_ID = "P2.1"
MILESTONE = "phase_2_2"  # programme milestone that owns P2.1; also unblocks Phase 2.1 readiness
PROGRAMME = "AGIB_EARNINGS_INTELLIGENCE"

FRESHNESS_SLA_DAYS = 14
RUNTIME_BUDGET_S = 2.5

# Default parse depth (index always full; XBRL detail limited for runtime)
DEFAULT_QUARTERLY_XBRL = 8
DEFAULT_ANNUAL_XBRL = 5

IC10_UNIVERSE = (
    "HDFCBANK",
    "RELIANCE",
    "TCS",
    "ETERNAL",
    "TMPV",
    "SUNPHARMA",
    "NTPC",
    "HAL",
    "ASIANPAINT",
    "ULTRACEMCO",
)

# Canonical income / balance / cashflow keys in Financial Statements Pack
INCOME_KEYS = (
    "revenue_from_operations",
    "other_income",
    "total_income",
    "expenses",
    "employee_benefit_expense",
    "finance_costs",
    "depreciation",
    "ebitda",
    "ebit",
    "pbt",
    "tax_expense",
    "pat",
    "pat_owners",
    "eps_basic",
    "eps_diluted",
)

BALANCE_KEYS = (
    "total_assets",
    "current_assets",
    "non_current_assets",
    "cash",
    "total_equity",
    "equity_share_capital",
    "equity_owners",
    "reserves",
    "face_value",
    "shares_outstanding",
    "deposits",
    "total_liabilities",
    "current_liabilities",
    "non_current_liabilities",
    "total_debt",
    "working_capital",
)

CASHFLOW_KEYS = (
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "free_cash_flow",
    "capex",
    "net_change_in_cash",
)
