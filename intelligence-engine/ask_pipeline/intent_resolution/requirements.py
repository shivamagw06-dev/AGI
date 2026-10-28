"""Evidence requirements derived from resolved intent (feeds IERE)."""

from __future__ import annotations

from typing import Any

_REQUIREMENTS: dict[str, list[str]] = {
    "Explain": ["FINANCIAL_METRICS", "RELATIONSHIP_GRAPH", "DOCUMENT_SECTIONS"],
    "Compare": ["FINANCIAL_METRICS", "RELATIONSHIP_GRAPH", "HISTORICAL_VALUATION", "OWNERSHIP"],
    "Analyse": [
        "FINANCIAL_METRICS",
        "CORPORATE_EVENTS",
        "DOCUMENT_SECTIONS",
        "RISK_FACTORS",
        "HISTORICAL_VALUATION",
    ],
    "Valuation": ["FINANCIAL_METRICS", "HISTORICAL_VALUATION", "OWNERSHIP", "DOCUMENT_SECTIONS"],
    "Portfolio": ["FINANCIAL_METRICS", "OWNERSHIP", "RELATIONSHIP_GRAPH", "CORPORATE_EVENTS"],
    "Education": ["FINANCIAL_METRICS", "DOCUMENT_SECTIONS"],
    "HistoricalReplay": ["FINANCIAL_METRICS", "DOCUMENT_SECTIONS", "CORPORATE_EVENTS", "TIMELINES"],
    "Risk": ["RISK_FACTORS", "FINANCIAL_METRICS", "CORPORATE_EVENTS", "MACRO_INDICATORS"],
    "Accounting": ["FINANCIAL_METRICS", "ACCOUNTING_NOTES", "DOCUMENT_SECTIONS"],
    "Industry": ["RELATIONSHIP_GRAPH", "MACRO_INDICATORS", "FINANCIAL_METRICS"],
    "Macro": ["MACRO_INDICATORS", "GOVERNMENT_POLICIES", "ALTERNATIVE_DATA"],
    "Government": ["GOVERNMENT_POLICIES", "MACRO_INDICATORS", "RELATIONSHIP_GRAPH"],
    "CorporateEvents": ["CORPORATE_EVENTS", "TIMELINES", "DOCUMENT_SECTIONS"],
    "Documents": [
        "DOCUMENT_SECTIONS",
        "RISK_FACTORS",
        "MANAGEMENT_COMMENTARY",
        "ACCOUNTING_NOTES",
        "INVESTOR_PRESENTATIONS",
    ],
    "CrossDomain": [
        "MACRO_INDICATORS",
        "GOVERNMENT_POLICIES",
        "ALTERNATIVE_DATA",
        "RELATIONSHIP_GRAPH",
        "FINANCIAL_METRICS",
        "CORPORATE_EVENTS",
    ],
    "CompanyOverview": ["FINANCIAL_METRICS", "CORPORATE_EVENTS", "DOCUMENT_SECTIONS", "RISK_FACTORS", "HISTORICAL_VALUATION"],
    "FinancialAnalysis": ["FINANCIAL_METRICS", "ACCOUNTING_NOTES", "MANAGEMENT_COMMENTARY", "TIMELINES"],
    "Earnings": ["FINANCIAL_METRICS", "CONFERENCE_CALLS", "MANAGEMENT_COMMENTARY", "CORPORATE_EVENTS", "TIMELINES"],
    "MarketMovement": ["MARKET_PRICES", "CORPORATE_EVENTS", "SECTOR_PERFORMANCE", "DOCUMENT_SECTIONS", "ALTERNATIVE_DATA"],
    "Ownership": ["OWNERSHIP", "TIMELINES", "CORPORATE_EVENTS"],
    "Screening": ["FINANCIAL_METRICS", "HISTORICAL_VALUATION", "OWNERSHIP", "MARKET_PRICES"],
    "Forecasting": ["FINANCIAL_METRICS", "MANAGEMENT_COMMENTARY", "EXPECTATIONS", "TIMELINES"],
    "Catalyst": ["CORPORATE_EVENTS", "TIMELINES", "MANAGEMENT_COMMENTARY", "DOCUMENT_SECTIONS"],
    "HistoricalChange": ["FINANCIAL_METRICS", "HISTORICAL_VALUATION", "TIMELINES", "CORPORATE_EVENTS"],
    "Unknown": ["FINANCIAL_METRICS", "DOCUMENT_SECTIONS"],
}

_WORKFLOWS: dict[str, list[str]] = {
    "Valuation": ["current_valuation", "historical_valuation", "peer_valuation", "growth", "returns", "margin_trend", "earnings_revisions"],
    "MarketMovement": ["price_volume", "sector_relative_performance", "recent_earnings", "announcements", "news", "valuation", "derivatives", "alpha_signals"],
    "Earnings": ["reported_vs_consensus", "segment_kpis", "margin_bridge", "guidance_change", "cash_flow", "management_commentary", "estimate_revisions"],
    "Comparison": ["normalize_metrics", "growth", "profitability", "cash_conversion", "balance_sheet", "valuation", "relative_risks"],
    "Compare": ["normalize_metrics", "growth", "profitability", "cash_conversion", "balance_sheet", "valuation", "relative_risks"],
    "Ownership": ["promoter_holding", "institutional_holding", "pledge", "quarterly_change", "price_context"],
    "Screening": ["parse_deterministic_filters", "query_numerical_truth", "apply_confidence_floor", "rank_results", "explain_results"],
    "Forecasting": ["historical_base_rates", "management_guidance", "consensus", "scenario_drivers", "confidence_bounds"],
    "Catalyst": ["scheduled_events", "unscheduled_events", "probability", "timing", "thesis_impact"],
    "HistoricalChange": ["current_state", "prior_state", "delta", "driver_attribution", "thesis_change"],
    "FinancialAnalysis": ["growth", "profitability", "cash_conversion", "balance_sheet", "capital_efficiency", "trend"],
    "CompanyOverview": ["business_model", "financial_quality", "valuation", "risks", "catalysts", "market_confirmation"],
}


def evidence_requirements(
    intent: str,
    *,
    concept_mode: bool,
    temporal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required = list(_REQUIREMENTS.get(intent) or _REQUIREMENTS["Unknown"])
    if temporal and temporal.get("is_historical"):
        if "TIMELINES" not in required:
            required.append("TIMELINES")
        if "HISTORICAL_VALUATION" not in required:
            required.append("HISTORICAL_VALUATION")
    return {
        "intent": intent,
        "evidence_types_required": required,
        "research_workflow": list(_WORKFLOWS.get(intent) or ["retrieve", "validate", "reason", "cite"]),
        "concept_mode": concept_mode,
        "require_company_object": (not concept_mode) and intent
        not in {"Education", "Explain", "Macro", "Government", "Industry", "CrossDomain", "Unknown"},
        "allow_empty_entity": concept_mode
        or intent
        in {
            "Education",
            "Explain",
            "Industry",
            "Macro",
            "Government",
            "CrossDomain",
            "Documents",
            "HistoricalReplay",
        },
        "fabricated": False,
    }
