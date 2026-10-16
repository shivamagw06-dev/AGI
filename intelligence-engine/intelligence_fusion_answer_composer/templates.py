"""Institutional answer templates — section skeletons only."""

from __future__ import annotations

TEMPLATES: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    # section_id, title, preferred provider ids for that section
    "company": (
        ("executive_summary", "Executive Summary", ("research_intelligence_engine", "forecast_intelligence_engine", "business_intelligence")),
        ("business_overview", "Business Overview", ("business_intelligence", "research_intelligence_engine", "capiq_ikt")),
        ("competitive_position", "Competitive Position", ("industry_intelligence", "business_intelligence")),
        ("financial_quality", "Financial Quality", ("investment_intelligence", "institutional_warehouse", "financial_statement_warehouse")),
        ("current_valuation", "Current Valuation", ("unified_valuation_engine", "valuation_terminal", "valuation_policy_engine")),
        ("historical_valuation", "Historical Valuation", ("historical_valuation_intelligence", "historical_intelligence")),
        ("valuation_attribution", "Valuation Attribution", ("valuation_attribution_engine",)),
        ("forecast_outlook", "Forecast Outlook", ("forecast_intelligence_engine",)),
        ("macro_exposure", "Macro Exposure", ("macro_intelligence_engine", "market_intelligence_engine")),
        ("ownership", "Institutional Ownership", ("institutional_warehouse", "investment_intelligence")),
        ("risks", "Risks", ("forecast_intelligence_engine", "research_intelligence_engine", "investment_intelligence")),
        ("catalysts", "Catalysts", ("forecast_intelligence_engine", "investment_intelligence")),
        ("monitoring", "Monitoring", ("research_intelligence_engine", "forecast_intelligence_engine", "investment_intelligence")),
        ("external_consensus", "External Consensus", ("valuation_consensus",)),
        ("conclusion", "Conclusion", ("research_intelligence_engine", "forecast_intelligence_engine")),
    ),
    "valuation": (
        ("current_valuation", "Current Valuation", ("unified_valuation_engine", "valuation_terminal")),
        ("historical_context", "Historical Context", ("historical_valuation_intelligence", "historical_intelligence")),
        ("applicable_model", "Applicable Valuation Model", ("valuation_policy_engine",)),
        ("why_current", "Why Current Valuation", ("valuation_attribution_engine", "unified_valuation_engine")),
        ("peer_comparison", "Peer Comparison", ("valuation_terminal", "valuation_attribution_engine")),
        ("external_consensus", "External Consensus", ("valuation_consensus",)),
        ("conclusion", "Research Conclusion", ("valuation_attribution_engine", "unified_valuation_engine")),
    ),
    "historical": (
        ("historical_valuation", "Historical Valuation", ("historical_valuation_intelligence",)),
        ("historical_bands", "Historical Bands", ("historical_valuation_intelligence", "historical_intelligence")),
        ("percentiles", "Historical Percentiles", ("historical_valuation_intelligence",)),
        ("regimes", "Regime Changes", ("historical_valuation_intelligence",)),
        ("similar_periods", "Previous Similar Periods", ("historical_valuation_intelligence", "valuation_attribution_engine")),
        ("context", "Historical Context", ("valuation_attribution_engine", "unified_valuation_engine")),
        ("conclusion", "Research Conclusion", ("historical_valuation_intelligence", "valuation_attribution_engine")),
    ),
    "forecast": (
        ("executive_outlook", "Executive Outlook", ("forecast_intelligence_engine", "research_intelligence_engine")),
        ("business_forecast", "Business Forecast", ("forecast_intelligence_engine", "business_intelligence")),
        ("bull", "Bull Scenario", ("forecast_intelligence_engine",)),
        ("base", "Base Scenario", ("forecast_intelligence_engine",)),
        ("bear", "Bear Scenario", ("forecast_intelligence_engine",)),
        ("assumptions", "Key Assumptions", ("forecast_intelligence_engine",)),
        ("confidence", "Confidence", ("forecast_intelligence_engine",)),
        ("catalysts", "Catalysts", ("forecast_intelligence_engine", "investment_intelligence")),
        ("risks", "Risks", ("forecast_intelligence_engine", "macro_intelligence_engine")),
        ("monitoring", "Monitoring", ("forecast_intelligence_engine", "research_intelligence_engine")),
    ),
    "macro": (
        ("executive_summary", "Executive Summary", ("macro_intelligence_engine", "market_intelligence_engine")),
        ("macro_regime", "Macro Regime", ("macro_intelligence_engine",)),
        ("transmission", "Transmission Mechanism", ("macro_intelligence_engine",)),
        ("sector_impact", "Sector Impact", ("macro_intelligence_engine", "market_intelligence_engine")),
        ("industry_impact", "Industry Impact", ("macro_intelligence_engine",)),
        ("company_exposure", "Company Exposure", ("macro_intelligence_engine",)),
        ("forecast", "Forecast", ("forecast_intelligence_engine", "macro_intelligence_engine")),
        ("risks", "Risks", ("macro_intelligence_engine",)),
        ("monitoring", "Monitoring", ("macro_intelligence_engine", "market_intelligence_engine")),
    ),
    "market": (
        ("market_summary", "Market Summary", ("market_intelligence_engine",)),
        ("breadth", "Breadth", ("market_intelligence_engine",)),
        ("flows", "Institutional Flows", ("market_intelligence_engine",)),
        ("rotation", "Sector Rotation", ("market_intelligence_engine",)),
        ("valuation", "Valuation", ("market_intelligence_engine", "historical_valuation_intelligence")),
        ("macro_context", "Macro Context", ("macro_intelligence_engine",)),
        ("priorities", "Research Priorities", ("market_intelligence_engine", "hedge_fund_screens")),
    ),
    "comparison": (
        ("executive_summary", "Executive Summary", ("research_intelligence_engine", "business_intelligence")),
        ("business", "Business Comparison", ("business_intelligence", "industry_intelligence")),
        ("financial", "Financial Comparison", ("institutional_warehouse", "investment_intelligence")),
        ("valuation", "Valuation Comparison", ("unified_valuation_engine", "valuation_terminal")),
        ("historical", "Historical Comparison", ("historical_valuation_intelligence", "valuation_attribution_engine")),
        ("forecast", "Forecast Comparison", ("forecast_intelligence_engine",)),
        ("macro", "Macro Comparison", ("macro_intelligence_engine",)),
        ("differences", "Key Differences", ("research_intelligence_engine", "valuation_attribution_engine")),
        ("conclusion", "Research Conclusion", ("research_intelligence_engine", "forecast_intelligence_engine")),
    ),
    "screen": (
        ("strategy", "Strategy", ("hedge_fund_screens",)),
        ("universe", "Universe", ("hedge_fund_screens", "market_intelligence_engine")),
        ("matches", "Matches", ("hedge_fund_screens",)),
        ("criteria", "Selection Criteria", ("hedge_fund_screens",)),
        ("top_candidates", "Top Candidates", ("hedge_fund_screens",)),
        ("factors", "Factor Summary", ("hedge_fund_screens", "institutional_warehouse")),
        ("valuation", "Valuation", ("unified_valuation_engine", "valuation_attribution_engine")),
        ("forecast", "Forecast", ("forecast_intelligence_engine",)),
        ("risks", "Risks", ("hedge_fund_screens", "research_intelligence_engine")),
        ("monitoring", "Monitoring", ("hedge_fund_screens", "forecast_intelligence_engine")),
    ),
    "attribution": (
        ("executive_summary", "Executive Summary", ("valuation_attribution_engine",)),
        ("premium", "Premium / Discount", ("valuation_attribution_engine", "historical_valuation_intelligence")),
        ("quality", "Business Quality", ("valuation_attribution_engine", "business_intelligence")),
        ("profitability", "Profitability", ("valuation_attribution_engine", "institutional_warehouse")),
        ("capital_allocation", "Capital Allocation", ("investment_intelligence", "research_intelligence_engine")),
        ("historical_behavior", "Historical Valuation Behavior", ("historical_valuation_intelligence",)),
        ("macro_factors", "Macro Factors", ("macro_intelligence_engine",)),
        ("ownership", "Institutional Ownership", ("institutional_warehouse", "valuation_attribution_engine")),
        ("expectations", "Future Expectations", ("forecast_intelligence_engine", "valuation_consensus")),
        ("conclusion", "Research Conclusion", ("valuation_attribution_engine", "research_intelligence_engine")),
    ),
}

# Map IFAC family → template id
FAMILY_TEMPLATE = {
    "company": "company",
    "company_intel": "company",
    "business": "company",
    "research": "company",
    "investment": "company",
    "valuation": "valuation",
    "historical": "historical",
    "forecast": "forecast",
    "macro": "macro",
    "market": "market",
    "comparison": "comparison",
    "compare": "comparison",
    "screen": "screen",
    "hedge_fund": "screen",
    "attribution": "attribution",
}


def template_for(family: str) -> str:
    return FAMILY_TEMPLATE.get(family, "company")


def sections_for(template_id: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return TEMPLATES.get(template_id) or TEMPLATES["company"]
