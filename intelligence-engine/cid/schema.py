"""CID schema constants — coverage categories and grades."""

from __future__ import annotations

CID_VERSION = "cid-v1.0.0"

COVERAGE_CATEGORIES: tuple[str, ...] = (
    "annual_reports",
    "quarterly_results",
    "investor_presentations",
    "financial_statements",
    "conference_calls",
    "corporate_announcements",
    "market_data",
    "valuation",
    "sector_kpis",
)

# Map LEO evidence_type → coverage category / document bucket
EVIDENCE_TO_CATEGORY: dict[str, str] = {
    "annual_report": "annual_reports",
    "quarterly_results": "quarterly_results",
    "investor_presentation": "investor_presentations",
    "earnings_transcript": "conference_calls",
    "financial_statements": "financial_statements",
    "corporate_announcement": "corporate_announcements",
    "market_data": "market_data",
    "valuation_metrics": "valuation",
    "sector_kpis": "sector_kpis",
    "macro": "market_data",
    "peer_comparison": "valuation",
    "esg_report": "annual_reports",
    "credit_rating": "corporate_announcements",
    "news": "corporate_announcements",
}


def coverage_grade(score: float) -> str:
    s = float(score or 0.0)
    if s >= 0.90:
        return "Institutional Grade"
    if s >= 0.70:
        return "Research Grade"
    if s >= 0.50:
        return "Partial"
    return "Insufficient"


def empty_dossier(ticker: str, *, company: str | None = None) -> dict:
    """Canonical empty CID object."""
    t = (ticker or "").upper()
    return {
        "cid_version": CID_VERSION,
        "ticker": t,
        "identity": {
            "company_name": company or t,
            "nse_symbol": t,
            "bse_code": None,
            "isin": None,
            "sector": None,
            "industry": None,
            "sub_sector": None,
            "market_cap": None,
            "index_membership": [],
        },
        "business_profile": {
            "business_model": None,
            "revenue_segments": [],
            "geographic_mix": [],
            "products": [],
            "services": [],
            "customers": [],
            "competitive_position": None,
            "economic_moat": None,
            "industry_structure": None,
        },
        "management": {
            "ceo": None,
            "cfo": None,
            "board": [],
            "promoter": None,
            "ownership": {},
            "capital_allocation_history": [],
            "governance_assessment": None,
        },
        "financial_statements": {
            "income_statement": {"annual": [], "quarterly": []},
            "balance_sheet": {"annual": [], "quarterly": []},
            "cash_flow": {"annual": [], "quarterly": []},
            "versions": [],
        },
        "financial_metrics": {},
        "sector_framework": {},
        "sector_kpis": {},
        "documents": {
            "annual_reports": [],
            "quarterly_results": [],
            "investor_presentations": [],
            "conference_call_transcripts": [],
            "credit_rating_reports": [],
            "esg_reports": [],
            "governance_reports": [],
        },
        "announcements": [],
        "market_data": {
            "current_price": None,
            "historical_prices": [],
            "market_cap": None,
            "enterprise_value": None,
            "volume": None,
            "fifty_two_week_high": None,
            "fifty_two_week_low": None,
            "valuation_multiples": {},
            "dividend_yield": None,
            "beta": None,
            "updated_at": None,
        },
        "valuation": {
            "preferred_methodology": [],
            "historical": [],
            "current": {},
            "sensitivity": {},
            "scenarios": [],
            "margin_of_safety": None,
            "target_range": None,
            "confidence": None,
        },
        "forecasts": {
            "revenue": [],
            "eps": [],
            "margin": [],
            "cash_flow": [],
            "roic": [],
            "accuracy": {},
            "historical": [],
        },
        "risks": {
            "business": [],
            "financial": [],
            "regulatory": [],
            "industry": [],
            "governance": [],
            "macro": [],
            "execution": [],
            "risk_score": None,
            "trend": None,
        },
        "catalysts": {
            "positive": [],
            "negative": [],
            "upcoming_events": [],
            "quarterly_results": [],
            "management_guidance": [],
            "policy_changes": [],
            "industry_changes": [],
        },
        "peer_comparison": {
            "peer_group": [],
            "valuation": {},
            "margins": {},
            "roic": {},
            "growth": {},
            "risk": {},
            "capital_allocation": {},
        },
        "finance_academy": {
            "economics": [],
            "accounting": [],
            "corporate_finance": [],
            "active_concepts": [],
            "courses": [],
        },
        "evidence_timeline": [],
        "coverage": {k: {"present": False, "count": 0, "score": 0.0} for k in COVERAGE_CATEGORIES},
        "coverage_score": 0.0,
        "coverage_grade": "Insufficient",
        "missing_evidence": list(COVERAGE_CATEGORIES),
        "latest_announcement": None,
        "latest_filing": None,
        "latest_presentation": None,
        "created_at": None,
        "updated_at": None,
        "source_policy": "permanent_institutional_memory",
        "answer_policy": "dossier_before_raw_apis",
    }
