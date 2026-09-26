"""Section generator — materialise sections for a report type."""

from __future__ import annotations

from typing import Any

from research_blueprint.blueprint_registry import DEFAULT_SECTION_OWNERS, get_blueprint

SECTION_LABELS: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "investment_thesis": "Investment Thesis",
    "business_quality": "Business Quality",
    "financial_quality": "Financial Quality",
    "valuation": "Valuation",
    "risk": "Risk",
    "forecast": "Forecast",
    "portfolio_fit": "Portfolio Fit",
    "committee_opinion": "Committee Opinion",
    "cio_summary": "CIO Summary",
    "appendix": "Appendix",
    "business_comparison": "Business Comparison",
    "financial_comparison": "Financial Comparison",
    "competitive_position": "Competitive Position",
    "valuation_comparison": "Valuation Comparison",
    "historical_comparison": "Historical Comparison",
    "risk_comparison": "Risk Comparison",
    "conclusion": "Conclusion",
    "definition": "Definition",
    "importance": "Importance",
    "calculation": "Calculation",
    "examples": "Examples",
    "common_mistakes": "Common Mistakes",
    "case_study": "Case Study",
    "summary": "Summary",
    "historical_valuation": "Historical Valuation",
    "historical_percentiles": "Historical Percentiles",
    "peer_comparison": "Peer Comparison",
    "macro_drivers": "Macro Drivers",
    "market_expectations": "Market Expectations",
    "scenario_analysis": "Scenario Analysis",
    "policy": "Policy",
    "transmission": "Transmission",
    "risks": "Risks",
    "sector_structure": "Sector Structure",
    "industry_dynamics": "Industry Dynamics",
    "company_overview": "Company Overview",
    "accounting_quality": "Accounting Quality",
    "management_assessment": "Management Assessment",
    "news_digest": "News Digest",
    "portfolio_construction": "Portfolio Construction",
    "stress_scenarios": "Stress Scenarios",
    "recommendation": "Recommendation",
    "key_levels": "Key Levels",
    "overnight_developments": "Overnight Developments",
    "session_recap": "Session Recap",
    "screening_criteria": "Screening Criteria",
    "screening_results": "Screening Results",
}


def generate_sections(report_type: str) -> dict[str, Any]:
    bp = get_blueprint(report_type)
    if not bp:
        return {"sections": [], "mandatory": [], "optional": [], "suppress_default": []}
    mandatory = list(bp["mandatory_sections"])
    optional = list(bp.get("optional_sections") or [])
    suppress = list(bp.get("suppress_default") or [])
    sections = []
    for key in mandatory + optional:
        sections.append(
            {
                "section_key": key,
                "label": SECTION_LABELS.get(key, key.replace("_", " ").title()),
                "default_owner": DEFAULT_SECTION_OWNERS.get(key, "Research Writer"),
                "default_priority": "mandatory" if key in mandatory else "optional",
            }
        )
    return {
        "sections": sections,
        "mandatory": mandatory,
        "optional": optional,
        "suppress_default": suppress,
        "report_name": bp.get("report_name"),
        "purpose": bp.get("purpose"),
        "audience": bp.get("audience"),
        "max_length_words": bp.get("max_length_words"),
        "output_style": bp.get("output_style"),
    }
