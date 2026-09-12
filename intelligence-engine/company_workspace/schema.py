"""CW-01 Company Workspace — schema constants."""

from __future__ import annotations

CW01_WORKSTREAM_ID = "CW-01"
CW01_PRODUCT = "Company Workspace"
CW01_VERSION = "cw-01-v1.0.0"
CW01_SUBSYSTEM = "company_workspace"
CW01_SPEC = "docs/CW_01_COMPANY_WORKSPACE.md"
# Not an office / not an engine — UX assembly surface that reuses Office SDK contracts.
CW01_SURFACE_ID = "cw-01"
CW01_DOMAIN = "knowledge"
CW01_ROLE = "company_user_experience"
CW01_REPORT_TYPE = "CompanyWorkspace"
CW01_RECOMMENDATION_POLICY = "presentation_only_no_buy_sell_no_analysis"

WORKSPACE_SECTIONS = (
    "overview",
    "company_profile",
    "business_quality",
    "financial_trends",
    "financial_relationships",
    "management_execution",
    "evidence_alignment",
    "business_strategy",
    "historical_timeline",
    "research_notes",
    "watchlist_status",
    "portfolio_references",
    "recent_events",
    "outstanding_questions",
    "confidence_summary",
    "evidence_references",
)

# Section key → source module (pass-through only)
SECTION_SOURCES = {
    "business_quality": "FIRE-06",
    "financial_trends": "FIRE-01",
    "financial_relationships": "FIRE-02",
    "business_strategy": "FIRE-03",
    "evidence_alignment": "FIRE-04",
    "management_execution": "FIRE-05",
    "research_notes": "IO-01",
    "watchlist_status": "WO-01",
    "portfolio_references": "PO-01",
}
