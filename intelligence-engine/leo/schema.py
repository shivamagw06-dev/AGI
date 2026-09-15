"""LEO schema constants and evidence-type taxonomy."""

from __future__ import annotations

LEO_VERSION = "leo-v1.0.0"

# Canonical evidence types used in plans, dossiers, and quality gates
EVIDENCE_TYPES = (
    "annual_report",
    "quarterly_results",
    "investor_presentation",
    "earnings_transcript",
    "financial_statements",
    "valuation_metrics",
    "market_data",
    "corporate_announcement",
    "sector_kpis",
    "macro",
    "peer_comparison",
    "broker_consensus",
    "esg_report",
    "credit_rating",
    "news",
)

# Rank order (lower = higher priority for reasoning)
RANK_WEIGHTS: dict[str, float] = {
    "annual_report": 1.0,
    "quarterly_results": 1.05,
    "financial_statements": 1.1,
    "investor_presentation": 1.2,
    "earnings_transcript": 1.25,
    "corporate_announcement": 1.3,
    "valuation_metrics": 1.4,
    "market_data": 1.5,
    "sector_kpis": 1.55,
    "macro": 1.7,
    "peer_comparison": 1.8,
    "broker_consensus": 1.9,
    "esg_report": 2.0,
    "credit_rating": 2.05,
    "news": 2.2,
}

# Intent → required evidence types
INTENT_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "investment_recommendation": (
        "annual_report",
        "quarterly_results",
        "investor_presentation",
        "corporate_announcement",
        "financial_statements",
        "valuation_metrics",
        "sector_kpis",
        "macro",
        "market_data",
        "peer_comparison",
    ),
    "valuation": (
        "financial_statements",
        "market_data",
        "valuation_metrics",
        "macro",
        "annual_report",
        "quarterly_results",
    ),
    "macro": ("macro", "market_data"),
    "news": ("corporate_announcement", "news", "market_data"),
    "sector": ("sector_kpis", "macro", "market_data", "peer_comparison"),
    "general_finance": ("market_data", "macro", "sector_kpis"),
}

# Map LEO evidence types → SIF assess_company_evidence keys
LEO_TO_SIF_EVIDENCE: dict[str, str] = {
    "annual_report": "latest_annual_report",
    "quarterly_results": "latest_quarterly_results",
    "investor_presentation": "latest_investor_presentation",
    "earnings_transcript": "recent_earnings_call",
    "corporate_announcement": "material_announcements",
    "financial_statements": "financial_statements",
    "valuation_metrics": "valuation_metrics",
    "sector_kpis": "sector_benchmarks",
    "market_data": "valuation_metrics",
}
