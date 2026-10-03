"""PO-01 Portfolio Office — schema constants."""

from __future__ import annotations

PO01_WORKSTREAM_ID = "PO-01"
PO01_OFFICE_ID = "po-01"
PO01_PRODUCT = "Portfolio Office"
PO01_VERSION = "po-01-v1.0.0"
PO01_SUBSYSTEM = "portfolio_office"
PO01_SPEC = "docs/PO_01_PORTFOLIO_OFFICE.md"
PO01_RECOMMENDATION_POLICY = "state_only_no_buy_sell_no_optimisation"
PO01_DOMAIN = "portfolio"

PSR_SECTIONS = (
    "portfolio_summary",
    "holdings",
    "cash",
    "sector_exposure",
    "industry_exposure",
    "country_exposure",
    "market_cap_distribution",
    "business_quality_distribution",
    "management_execution_distribution",
    "concentration",
    "confidence_summary",
    "evidence_references",
)

PSR_SECTION_TITLES = {
    "portfolio_summary": "Portfolio Summary",
    "holdings": "Holdings",
    "cash": "Cash",
    "sector_exposure": "Sector Exposure",
    "industry_exposure": "Industry Exposure",
    "country_exposure": "Country Exposure",
    "market_cap_distribution": "Market Cap Distribution",
    "business_quality_distribution": "Business Quality Distribution",
    "management_execution_distribution": "Management Execution Distribution",
    "concentration": "Concentration",
    "confidence_summary": "Confidence Summary",
    "evidence_references": "Evidence References",
}

SNAPSHOT_KINDS = ("current", "daily", "manual", "historical")
PORTFOLIO_STATUSES = ("active", "closed", "draft")
