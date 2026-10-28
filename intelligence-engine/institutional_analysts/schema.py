"""Institutional Analyst Framework V1 — constants (not an engine)."""

PROGRAMME = "AGIB_INSTITUTIONAL_ANALYST_FRAMEWORK_V1"
PROGRAMME_SHORT = "IAF"
IAF_VERSION = "iaf-v1.1.0"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"

ANALYST_ROLES = [
    "business",
    "financial",
    "valuation",
    "market",
    "sector",
    "macro",
    "risk",
    "management",
    "ownership",
]

# Public-facing section ownership (never expose internal engine names)
SECTION_OWNERS = {
    "executive_summary": "cio",
    "institutional_view": "committee",
    "business_intelligence": "business",
    "financial_intelligence": "financial",
    "valuation_intelligence": "valuation",
    "market_intelligence": "market",
    "sector_intelligence": "sector",
    "macro_intelligence": "macro",
    "risks": "risk",
    "management": "management",
    "ownership": "ownership",
    "scenarios": "cio",
    "conclusion": "cio",
    "recommendation_status": "recommendation_gate",
    "committee_minutes": "committee",
    "disagreement_matrix": "committee",
    "what_changed": "committee",
}

PUBLIC_OWNER_LABELS = {
    "cio": "Chief Investment Officer",
    "committee": "Investment Committee",
    "business": "Business Analyst",
    "financial": "Financial Analyst",
    "valuation": "Valuation Analyst",
    "market": "Market Analyst",
    "sector": "Sector Analyst",
    "macro": "Macro Analyst",
    "risk": "Risk Analyst",
    "management": "Management Analyst",
    "ownership": "Ownership Analyst",
    "recommendation_gate": "Recommendation Gate",
}
