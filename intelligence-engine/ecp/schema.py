"""ECP constants — evidence checklists and completion taxonomy."""

from __future__ import annotations

ECP_VERSION = "ecp-v1.0.0"

# Market data checklist (mission)
MARKET_DATA_FIELDS = (
    "current_price",
    "market_cap",
    "enterprise_value",
    "shares_outstanding",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "volume",
    "liquidity",
    "dividend_yield",
)

# Valuation checklist
VALUATION_FIELDS = (
    "trailing_pe",
    "forward_pe",
    "ev_ebitda",
    "price_to_book",
    "price_to_sales",
    "peg",
    "dcf",
    "historical_valuation",
    "peer_valuation",
)

# Financial metrics checklist
FINANCIAL_FIELDS = (
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "quarterly_results",
    "annual_results",
    "revenue_growth",
    "eps_growth",
    "operating_margin",
    "profit_margin",
    "roe",
    "roce",
    "debt",
    "free_cash_flow",
)

# Earnings checklist
EARNINGS_FIELDS = (
    "latest_results",
    "guidance",
    "estimate_revisions",
    "consensus",
    "historical_surprises",
)

# Company knowledge checklist
COMPANY_KNOWLEDGE_FIELDS = (
    "business_model",
    "competitive_position",
    "management",
    "products",
    "brands",
    "customers",
    "suppliers",
    "risks",
    "catalysts",
    "historical_research",
    "prediction_history",
)

# Map LEO missing evidence types → ECP completion families
LEO_TYPE_TO_FAMILY: dict[str, str] = {
    "market_data": "market_data",
    "valuation_metrics": "valuation",
    "financial_statements": "financials",
    "quarterly_results": "financials",
    "annual_report": "financials",
    "earnings_transcript": "earnings",
    "investor_presentation": "company_knowledge",
    "sector_kpis": "sector_kpis",
    "peer_comparison": "valuation",
    "corporate_announcement": "company_knowledge",
    "macro": "macro",
    "broker_consensus": "earnings",
}

# CID coverage category → LEO evidence type (for re-gate)
CID_TO_LEO: dict[str, str] = {
    "annual_reports": "annual_report",
    "quarterly_results": "quarterly_results",
    "investor_presentations": "investor_presentation",
    "financial_statements": "financial_statements",
    "conference_calls": "earnings_transcript",
    "corporate_announcements": "corporate_announcement",
    "market_data": "market_data",
    "valuation": "valuation_metrics",
    "sector_kpis": "sector_kpis",
}

# Providers ECP may soft-call (priority order for completion attempts)
COMPLETION_PROVIDERS = (
    "market_data_client",
    "dvc",
    "yahoo",
    "cid",
    "kip",
    "knowledge_foundation",
)
