"""IKT-01 — 24 structured institutional tables (schema only; no fabricated data).

Every field is populated only when a real collector/source writes it via
`upsert_fact`. Unpopulated fields stay NULL and are reported as "missing".
"""

from __future__ import annotations

IKT_VERSION = "ikt-v1.0.0"
IKT_WORKSTREAM_ID = "IUDF-V1.5"
IKT_SPEC = "docs/AGI_V15_IUDF_INSTITUTIONAL_KNOWLEDGE_TABLES.md"

TABLE_DEFS: dict[str, dict[str, object]] = {
    "company_master": {
        "label": "Company Master",
        "fields": (
            "company_id",
            "company_name",
            "ticker",
            "isin",
            "sector",
            "industry",
            "exchange",
            "website",
            "cin",
            "fiscal_year_end",
            "country",
            "status",
            # Capital IQ / screener-export extensions (bulk_sheet.py)
            "currency",
            "company_type",
            "native_name",
            "parent_company",
            "external_id",
            "research_coverage_count",
        ),
        "keyed_by_period": False,
    },
    "financial_statements": {
        "label": "Financial Statements",
        "fields": (
            "fy",
            "quarter",
            "revenue",
            "ebitda",
            "ebit",
            "pat",
            "eps",
            "operating_cash_flow",
            "total_debt",
            "cash",
            "roe",
            "roce",
            "ebitda_margin",
            "net_margin",
            "source",
        ),
        "keyed_by_period": True,
    },
    "market_data": {
        "label": "Market Data",
        "fields": (
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "market_cap",
            "enterprise_value",
            "week52_high",
            "week52_low",
            "returns_1m",
            "returns_1y",
            # Capital IQ / screener-export extensions (bulk_sheet.py)
            "returns_ytd",
            "returns_1d",
            "returns_1w",
            "returns_3m",
            "returns_6m",
            "returns_9m",
            "returns_3y",
            "returns_5y",
            "next_earnings_date_announced",
            "next_earnings_date_expected",
        ),
        "keyed_by_period": True,
    },
    "valuation": {
        "label": "Valuation",
        "fields": (
            "pe",
            "pb",
            "ev_ebitda",
            "ev_sales",
            "dividend_yield",
            "fcf_yield",
            "peg",
            "intrinsic_value",
            "margin_of_safety",
        ),
        "keyed_by_period": False,
    },
    "shareholding": {
        "label": "Shareholding",
        "fields": (
            "quarter",
            "promoter",
            "fii",
            "dii",
            "mutual_funds",
            "insurance",
            "retail",
            "government",
            "pledged_pct",
        ),
        "keyed_by_period": True,
    },
    "corporate_actions": {
        "label": "Corporate Actions",
        "fields": (
            "dividend",
            "bonus",
            "split",
            "rights",
            "buyback",
            "merger",
            "acquisition",
            "demerger",
            "fund_raise",
        ),
        "keyed_by_period": True,
    },
    "investor_presentations": {
        "label": "Investor Presentations",
        "fields": (
            "document",
            "quarter",
            "kpis",
            "capex",
            "products",
            "segments",
            "growth",
            "expansion",
            "guidance",
        ),
        "keyed_by_period": True,
    },
    "earnings_call_transcripts": {
        "label": "Earnings Call Transcripts",
        "fields": (
            "speaker",
            "role",
            "question",
            "answer",
            "topic",
            "sentiment",
            "confidence",
        ),
        "keyed_by_period": True,
    },
    "annual_reports": {
        "label": "Annual Reports",
        "fields": (
            "document",
            "year",
            "chairman_message",
            "business_overview",
            "risk_factors",
            "strategy",
            "capex",
            "esg",
        ),
        "keyed_by_period": True,
    },
    "business_model": {
        "label": "Business Model",
        "fields": (
            "business_segments",
            "revenue_mix",
            "products",
            "services",
            "customers",
            "geography",
            "competitive_position",
            "description",
            # Capital IQ / screener-export extensions (bulk_sheet.py)
            "description_short",
            "index_constituents",
            "industry_classifications",
            "investors",
            "subsidiaries_count",
        ),
        "keyed_by_period": False,
    },
    "management": {
        "label": "Management",
        "fields": (
            "ceo",
            "cfo",
            "board",
            "independent_directors",
            "auditor",
            "management_changes",
        ),
        "keyed_by_period": False,
    },
    "guidance": {
        "label": "Guidance",
        "fields": (
            "revenue_guidance",
            "margin_guidance",
            "capex_guidance",
            "growth_guidance",
            "commentary",
        ),
        "keyed_by_period": True,
    },
    "news": {
        "label": "News",
        "fields": ("headline", "summary", "category", "impact", "sentiment", "evidence"),
        "keyed_by_period": False,
    },
    "risks": {
        "label": "Risks",
        "fields": ("risk", "probability", "impact", "mitigation", "evidence"),
        "keyed_by_period": False,
    },
    "catalysts": {
        "label": "Catalysts",
        "fields": ("catalyst", "expected_impact", "timeline", "probability"),
        "keyed_by_period": False,
    },
    "esg": {
        "label": "ESG",
        "fields": ("carbon", "water", "energy", "governance", "csr"),
        "keyed_by_period": False,
    },
    "macro_exposure": {
        "label": "Macro Exposure",
        "fields": (
            "interest_rate_sensitivity",
            "usdinr_sensitivity",
            "oil_sensitivity",
            "inflation",
            "gdp",
            "policy_exposure",
        ),
        "keyed_by_period": False,
    },
    "competitors": {
        "label": "Competitors",
        "fields": ("peer", "revenue", "margin", "valuation", "growth", "market_share"),
        "keyed_by_period": False,
    },
    "products": {
        "label": "Products",
        "fields": ("product", "revenue_contribution", "growth", "market", "pricing", "product_description"),
        "keyed_by_period": False,
    },
    "customers": {
        "label": "Customers",
        "fields": ("customer_type", "region", "revenue_pct", "growth"),
        "keyed_by_period": False,
    },
    "contracts": {
        "label": "Contracts",
        "fields": ("order_wins", "government_contracts", "private_contracts", "tender_value"),
        "keyed_by_period": False,
    },
    "litigation": {
        "label": "Litigation",
        "fields": ("court_cases", "regulatory_issues", "sebi", "nclt", "tax"),
        "keyed_by_period": False,
    },
    "credit_ratings": {
        "label": "Credit Ratings",
        "fields": ("agency", "rating", "outlook", "date"),
        "keyed_by_period": False,
    },
    "knowledge_metadata": {
        "label": "Knowledge Metadata",
        "fields": (
            "evidence_count",
            "claims",
            "knowledge_confidence",
            "institutional_coverage",
            "research_ready",
            "claim_safe",
            "knowledge_version",
        ),
        "keyed_by_period": False,
    },
}


def valid_table(name: str) -> bool:
    return str(name or "").strip().lower() in TABLE_DEFS


def table_fields(name: str) -> tuple[str, ...]:
    meta = TABLE_DEFS.get(str(name or "").strip().lower())
    return tuple(meta["fields"]) if meta else ()  # type: ignore[index]
