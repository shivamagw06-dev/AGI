"""CMS schema constants."""

from __future__ import annotations

CMS_VERSION = "company-monitor-v1.0.0"
PROGRAMME = "AGI_COMPANY_MONITOR"
PROGRAMME_SHORT = "Company Monitoring System"

# Reuse CID tracked universe as default monitor set
DEFAULT_UNIVERSE = (
    "HDFCBANK",
    "INFY",
    "RELIANCE",
    "ULTRACEMCO",
    "ASIANPAINT",
    "TATASTEEL",
    "SUNPHARMA",
    "POWERGRID",
    "NESTLEIND",
    "TCS",
)

MONITOR_CHANNELS = (
    "price",
    "financial_statements",
    "quarterly_results",
    "annual_reports",
    "investor_presentations",
    "corporate_actions",
    "dividends",
    "management_changes",
    "shareholding_changes",
    "ratings",
    "news",
    "macro_exposure",
    "sector_changes",
    "house_view",
    "predictions",
)

CHANGE_TYPES = (
    "revenue_acceleration",
    "revenue_deceleration",
    "margin_expansion",
    "margin_compression",
    "debt_increase",
    "debt_reduction",
    "cash_flow_deterioration",
    "cash_flow_improvement",
    "capital_raising",
    "buybacks",
    "dividend_changes",
    "management_changes",
    "guidance_revisions",
    "rating_revisions",
    "valuation_expansion",
    "valuation_compression",
    "roe_improvement",
    "roe_deterioration",
)

SIGNIFICANCE = ("Low", "Medium", "High", "Critical")
