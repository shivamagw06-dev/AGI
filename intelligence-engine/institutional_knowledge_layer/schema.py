"""IKL — Institutional Knowledge Intelligence Layer (Gather → Memory → Ask)."""

from __future__ import annotations

import time
from typing import Any

IKL_VERSION = "1.0.0"
IKL_SCHEMA_VERSION = "ikl-1.0"
IKL_CODE = "IKL"
PROGRAMME = "Institutional Knowledge Intelligence Layer"
PROGRAMME_SHORT = "IKL"
MISSION = (
    "Convert every ingested document into persistent institutional knowledge "
    "before any user asks a question. Never a second knowledge system — "
    "façade over CID, Company Memory, KF/KC, KIL, and Knowledge Graph."
)

# Ask retrieval order (memory before raw documents)
ASK_RETRIEVAL_ORDER = (
    "company_memory",
    "industry_memory",
    "macro_memory",
    "knowledge_graph",
    "structured_kpis",
    "historical_timeline",
    "raw_documents",
    "live_search",
)

EXTRACTION_SLOTS = (
    "companies",
    "industries",
    "themes",
    "products",
    "segments",
    "management",
    "countries",
    "commodities",
    "competitors",
    "suppliers",
    "customers",
    "government_policies",
    "financial_kpis",
    "guidance",
    "risks",
    "opportunities",
    "events",
    "relationships",
)

COMPANY_MEMORY_SLOTS = (
    "identity",
    "business_model",
    "revenue_segments",
    "products_services",
    "geographic_exposure",
    "competitive_position",
    "management_timeline",
    "capital_allocation",
    "historical_kpis",
    "valuation_drivers",
    "key_risks",
    "investment_highlights",
    "industry_relationships",
    "macro_exposure",
    "latest_guidance",
    "document_timeline",
    "evidence_confidence",
    "last_updated",
)

INDUSTRY_MEMORY_SLOTS = (
    "industry_structure",
    "market_size",
    "growth_drivers",
    "competitive_dynamics",
    "regulation",
    "supply_chain",
    "typical_kpis",
    "valuation_frameworks",
    "historical_cycles",
    "current_trends",
    "representative_companies",
    "macro_sensitivity",
    "document_timeline",
    "evidence_confidence",
    "last_updated",
)

MACRO_MEMORY_TOPICS = (
    "interest_rates",
    "inflation",
    "gdp",
    "fiscal_policy",
    "monetary_policy",
    "currencies",
    "commodities",
    "oil",
    "gold",
    "steel",
    "power",
    "real_estate",
    "trade",
    "government_schemes",
    "historical_events",
)

RELATIONSHIP_TYPES = (
    "belongs_to",
    "competes_with",
    "supplies",
    "customer_of",
    "affected_by",
    "exposed_to",
    "benefits_from",
    "hurt_by",
    "linked_to",
)

DOCUMENT_TYPES = (
    "annual_report",
    "quarterly_report",
    "investor_presentation",
    "earnings_call",
    "cms_article",
    "research_note",
    "government_release",
    "macro_report",
    "book_summary",
    "filing",
    "unknown",
)

DELTA_KINDS = (
    "management_change",
    "guidance_revision",
    "strategy_change",
    "capex_change",
    "risk_change",
    "business_model_evolution",
    "margin_change",
    "capital_allocation_change",
)


def now_ts() -> float:
    return time.time()


def empty_company_memory(ticker: str) -> dict[str, Any]:
    t = (ticker or "").strip().upper() or "UNKNOWN"
    slots: dict[str, Any] = {s: [] if s != "identity" else {"ticker": t} for s in COMPANY_MEMORY_SLOTS}
    slots["identity"] = {"ticker": t}
    slots["evidence_confidence"] = 0.0
    slots["last_updated"] = None
    return {
        "schema_version": IKL_SCHEMA_VERSION,
        "kind": "company",
        "key": t,
        "slots": slots,
        "source_ids": [],
        "update_count": 0,
        "created_at": now_ts(),
        "updated_at": now_ts(),
    }


def empty_industry_memory(industry: str) -> dict[str, Any]:
    key = (industry or "").strip() or "unknown"
    slots: dict[str, Any] = {s: [] for s in INDUSTRY_MEMORY_SLOTS}
    slots["evidence_confidence"] = 0.0
    slots["last_updated"] = None
    return {
        "schema_version": IKL_SCHEMA_VERSION,
        "kind": "industry",
        "key": key,
        "slots": slots,
        "source_ids": [],
        "update_count": 0,
        "created_at": now_ts(),
        "updated_at": now_ts(),
    }


def empty_macro_memory(topic: str) -> dict[str, Any]:
    key = (topic or "").strip().lower() or "unknown"
    return {
        "schema_version": IKL_SCHEMA_VERSION,
        "kind": "macro",
        "key": key,
        "events": [],
        "affected_industries": [],
        "notes": [],
        "source_ids": [],
        "evidence_confidence": 0.0,
        "update_count": 0,
        "created_at": now_ts(),
        "updated_at": now_ts(),
        "last_updated": None,
    }
