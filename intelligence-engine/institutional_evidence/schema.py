"""IEP-01 / v1.1.1 — Institutional Evidence Platform constants.

AGI v1.1.1: operating system for institutional knowledge.
Intelligence engines consume durable knowledge — they do not substitute for it.
"""

from __future__ import annotations

IEP_WORKSTREAM_ID = "IEP-01"
IEP_PRODUCT = "Institutional Evidence Platform"
IEP_VERSION = "iep-01-v1.1.2"
IEP_SPEC = "docs/AGI_IEP_01_INSTITUTIONAL_EVIDENCE_PLATFORM.md"
IEP_ROLE = "institutional_knowledge_os"

ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True  # engines frozen; evidence/knowledge plane expands
AGI_PLATFORM_VERSION = "1.1.2-kil"

MISSION_STATEMENT = (
    "AGI is an Institutional Knowledge Platform that continuously acquires, "
    "validates, normalizes, versions, and preserves institutional evidence, "
    "transforming raw market information into a canonical knowledge base from "
    "which research, investment decisions, portfolio intelligence, and future "
    "AI capabilities are derived. Every material conclusion must be explainable, "
    "reproducible, and traceable to primary evidence."
)

GUIDING_PRINCIPLE = (
    "Today: AGI is primarily an intelligence platform with data feeding engines. "
    "Target: AGI is a knowledge platform where data becomes durable institutional "
    "knowledge, and intelligence engines simply consume that knowledge."
)

DESIGN_PRINCIPLES = (
    "No research without evidence",
    "No recommendation without canonical financial statements",
    "No narrative without lineage",
    "Every material claim maps to primary evidence",
    "Missing evidence blocks publication",
    "Every downstream engine consumes a single canonical Research Pack",
    "Nothing enters AGI without data governance",
    "Every document references an immutable Entity ID",
)

# Pipeline (Layer 0 first)
KNOWLEDGE_OS_PIPELINE = (
    "External Provider",
    "Data Governance",
    "Evidence Acquisition",
    "Canonical Normalization",
    "Data Quality Engine",
    "Evidence Registry",
    "Company Memory + Timeline",
    "Evidence Graph + Claims",
    "Knowledge Graph",
    "Financial Intelligence",
    "Decision Eligibility",
    "Decision Engine",
    "Research Lifecycle",
    "Publishing",
)

ANTI_PIPELINE = ("Raw Data", "LLM", "Research Note")

# Phase 1 — Top 20 Indian companies (cross-sector). Do not scale before quality.
PHASE1_UNIVERSE = (
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "SUNPHARMA",
    "TITAN",
    "ULTRACEMCO",
    "NTPC",
    "POWERGRID",
    "NESTLEIND",
)

PHASE1_TOP20 = (
    {"ticker": "RELIANCE", "company": "Reliance Industries", "sector": "Energy / Conglomerate", "entity_seq": 43},
    {"ticker": "TCS", "company": "Tata Consultancy Services", "sector": "IT Services", "entity_seq": 1},
    {"ticker": "HDFCBANK", "company": "HDFC Bank", "sector": "Banks", "entity_seq": 2},
    {"ticker": "INFY", "company": "Infosys", "sector": "IT Services", "entity_seq": 3},
    {"ticker": "ICICIBANK", "company": "ICICI Bank", "sector": "Banks", "entity_seq": 4},
    {"ticker": "HINDUNILVR", "company": "Hindustan Unilever", "sector": "FMCG", "entity_seq": 5},
    {"ticker": "ITC", "company": "ITC", "sector": "FMCG", "entity_seq": 6},
    {"ticker": "SBIN", "company": "State Bank of India", "sector": "Banks", "entity_seq": 7},
    {"ticker": "BHARTIARTL", "company": "Bharti Airtel", "sector": "Telecom", "entity_seq": 8},
    {"ticker": "KOTAKBANK", "company": "Kotak Mahindra Bank", "sector": "Banks", "entity_seq": 9},
    {"ticker": "LT", "company": "Larsen & Toubro", "sector": "Industrials", "entity_seq": 10},
    {"ticker": "AXISBANK", "company": "Axis Bank", "sector": "Banks", "entity_seq": 11},
    {"ticker": "ASIANPAINT", "company": "Asian Paints", "sector": "Materials", "entity_seq": 12},
    {"ticker": "MARUTI", "company": "Maruti Suzuki", "sector": "Auto", "entity_seq": 13},
    {"ticker": "SUNPHARMA", "company": "Sun Pharmaceutical", "sector": "Pharma", "entity_seq": 14},
    {"ticker": "TITAN", "company": "Titan Company", "sector": "Consumer Discretionary", "entity_seq": 15},
    {"ticker": "ULTRACEMCO", "company": "UltraTech Cement", "sector": "Materials", "entity_seq": 16},
    {"ticker": "NTPC", "company": "NTPC", "sector": "Utilities", "entity_seq": 17},
    {"ticker": "POWERGRID", "company": "Power Grid Corporation", "sector": "Utilities", "entity_seq": 18},
    {"ticker": "NESTLEIND", "company": "Nestlé India", "sector": "FMCG", "entity_seq": 19},
)

# Explicit Institutional Coverage Complete criteria (Phase 1)
PHASE1_ACCEPTANCE_CRITERIA = (
    "financial_statements_10y",
    "complete_annual_reports",
    "quarterly_history",
    "earnings_presentations",
    "earnings_call_transcripts",
    "corporate_actions",
    "shareholding_history",
    "segment_history",
    "company_timeline",
    "canonical_financials",
    "company_memory",
    "evidence_registry",
    "knowledge_graph",
    "research_readiness_target",
    "zero_unsupported_material_claims",
    "reproducible_research_note",
)

CANONICAL_DOMAIN_MODELS = (
    "CanonicalCompany",
    "CanonicalFinancialStatements",
    "CanonicalMarketData",
    "CanonicalCorporateActions",
    "CanonicalShareholding",
    "CanonicalManagementGuidance",
    "CanonicalTranscript",
    "CanonicalNewsEvent",
    "CanonicalMacroSeries",
    "CanonicalValuation",
    "CanonicalForecast",
)

DOCUMENT_TYPES = (
    "annual_report",
    "quarterly_results",
    "earnings_presentation",
    "earnings_transcript",
    "shareholding",
    "corporate_action",
    "exchange_announcement",
    "xbrl_filing",
    "nse_xbrl",
    "ir_document",
    "news",
    "macro",
    "market_quote",
    "market_secondary",
    "other",
)

PRIMARY_DOCUMENT_TYPES = (
    "annual_report",
    "quarterly_results",
    "earnings_presentation",
    "earnings_transcript",
    "nse_xbrl",
    "xbrl_filing",
    "shareholding",
    "corporate_action",
    "exchange_announcement",
    "ir_document",
)

PRIMARY_SOURCES = (
    "nse",
    "bse",
    "company_ir",
    "annual_report",
    "quarterly_results",
    "earnings_presentation",
    "earnings_transcript",
    "shareholding",
    "corporate_actions",
)

SECONDARY_SOURCES = (
    "yahoo",
    "groww",
    "finnhub",
    "news",
    "macro",
    "fred",
    "rbi",
    "firecrawl",
    "exa",
)

AUTHORITY_SCORES = {
    "nse": 0.95,
    "bse": 0.95,
    "company_ir": 0.9,
    "annual_report": 0.95,
    "quarterly_results": 0.9,
    "earnings_intelligence": 0.85,
    "financial_statements_engine": 0.9,
    "nse_xbrl": 0.95,
    "yahoo": 0.45,
    "groww": 0.4,
    "finnhub": 0.45,
    "news": 0.35,
    "macro": 0.5,
    "live_institutional_data": 0.55,
    "market_secondary": 0.4,
}

FRESHNESS_SLA_DAYS = {
    "annual_report": 400,
    "quarterly_results": 120,
    "earnings_presentation": 120,
    "earnings_transcript": 120,
    "nse_xbrl": 120,
    "xbrl_filing": 120,
    "shareholding": 120,
    "corporate_action": 30,
    "market_secondary": 7,
    "news": 14,
    "macro": 60,
}

MANDATORY_PACK_COMPONENTS = (
    "financials",
    "evidence",
    "company_memory",
    "research_readiness",
)

READINESS_WEIGHTS = {
    "primary_filings": 15,
    "financial_statements": 25,
    "segment_coverage": 10,
    "valuation_inputs": 10,
    "evidence_completeness": 15,
    "freshness": 10,
    "knowledge_graph": 5,
    "financial_intelligence": 5,
    "decision_consistency": 5,
}

RESEARCH_READY_THRESHOLD = 70.0
EVIDENCE_QUALITY_PUBLISH_THRESHOLD = 70.0
FRESHNESS_MAX_DAYS = 120
MIN_FINANCIAL_YEARS = 10

FORBIDDEN_INVENTED_FIELDS = (
    "revenue",
    "eps",
    "ebitda",
    "debt",
    "margins",
    "arpu",
    "grm",
    "capex",
    "valuation",
    "pat",
    "roe",
    "roce",
)

BLOCKED_RECOMMENDATIONS = (
    "BUY",
    "SELL",
    "OVERWEIGHT",
    "UNDERWEIGHT",
    "STRONG BUY",
    "STRONG SELL",
)

ALLOWED_WHEN_BLOCKED = (
    "NO RECOMMENDATION",
    "MONITOR",
    "NEUTRAL",
)

RESEARCH_LIFECYCLE_STATES = (
    "draft",
    "analyst_review",
    "published",
    "evidence_changed",
    "marked_stale",
    "auto_refresh",
    "republished",
)

QUALITY_DIMENSIONS = (
    "completeness",
    "consistency",
    "freshness",
    "authority",
    "coverage",
    "confidence",
    "accounting_validation",
    "duplicate_detection",
    "schema_validation",
)

ENTITY_ID_PREFIX = "AGI-COMPANY-"
