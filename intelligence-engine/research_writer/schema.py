"""Institutional Research Writer V1 — presentation layer constants (not an engine)."""

PROGRAMME = "AGIB_INSTITUTIONAL_RESEARCH_WRITER_V1"
PROGRAMME_SHORT = "IRW"
IRW_VERSION = "irw-v1.0.0"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"

REPORT_TYPES = [
    "Company Initiation",
    "Company Update",
    "Quarterly Earnings Review",
    "Sector Research",
    "Macro Research",
    "Theme Research",
    "Portfolio Review",
    "Investment Committee Minutes",
    "Morning Brief",
    "Evening Brief",
]

SECTION_ORDER = [
    "executive_summary",
    "institutional_view",
    "investment_thesis",
    "business_intelligence",
    "financial_intelligence",
    "valuation_intelligence",
    "market_intelligence",
    "sector_intelligence",
    "macro_intelligence",
    "management",
    "ownership",
    "risks",
    "scenarios",
    "catalysts",
    "conclusion",
]

# IRW never mutates these intelligence fields
IMMUTABLE_FIELDS = [
    "confidence",
    "committee_vote",
    "committee_decision",
    "disagreement_matrix",
    "recommendation_readiness",
    "scores",
    "evidence",
]
