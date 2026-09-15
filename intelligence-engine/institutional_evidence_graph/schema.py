"""IEG — Institutional Evidence Graph schemas."""

from __future__ import annotations

from typing import Any

IEG_VERSION = "institutional-evidence-graph-v1.0.0"
PROGRAMME = "AGIB v3.6 – Phase 2 Institutional Intelligence · Sprint 2.1 Evidence Graph"
MODULE_CODE = "IEG"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "planner": True,
    "reasoning_frozen": True,
    "no_new_intelligence_domains": True,
    "soft_wire_only": True,
    "deterministic_only": True,
    "no_llm_graph_construction": True,
    "never_fabricate_relationships": True,
    "point_in_time_integrity": True,
    "soft_read_ieri_iere_ikg_only": True,
}

# Company domain tree — every entity should know these facets
ENTITY_DOMAINS: tuple[str, ...] = (
    "financials",
    "segments",
    "products",
    "customers",
    "suppliers",
    "competitors",
    "management",
    "shareholding",
    "risks",
    "valuation",
    "corporate_actions",
    "news",
    "earnings",
    "guidance",
    "macro_exposure",
    "esg",
    "credit",
    "historical_events",
)

# Map IERE evidence types → domains
EVIDENCE_TYPE_TO_DOMAIN: dict[str, str] = {
    "FINANCIAL_METRICS": "financials",
    "HISTORICAL_VALUATION": "valuation",
    "CORPORATE_EVENTS": "corporate_actions",
    "DOCUMENT_SECTIONS": "financials",
    "ACCOUNTING_NOTES": "financials",
    "RISK_FACTORS": "risks",
    "MANAGEMENT_COMMENTARY": "management",
    "CONFERENCE_CALLS": "earnings",
    "INVESTOR_PRESENTATIONS": "guidance",
    "OWNERSHIP": "shareholding",
    "TIMELINES": "historical_events",
    "MACRO_INDICATORS": "macro_exposure",
    "GOVERNMENT_POLICIES": "macro_exposure",
    "ALTERNATIVE_DATA": "news",
    "RELATIONSHIP_GRAPH": "competitors",
}

# Map IERI relationship buckets → domains
RELATIONSHIP_BUCKET_TO_DOMAIN: dict[str, str] = {
    "suppliers": "suppliers",
    "major_customers": "customers",
    "competitors": "competitors",
    "commodity_inputs": "macro_exposure",
    "commodity_outputs": "macro_exposure",
    "government_relationships": "macro_exposure",
    "bank_relationships": "credit",
    "strategic_partners": "customers",
    "joint_ventures": "segments",
    "industry_relationships": "competitors",
    "infrastructure_dependencies": "suppliers",
}

# Source → default evidence strength (0–10 institutional scale)
SOURCE_STRENGTH: dict[str, float] = {
    "annual_report": 10.0,
    "annual_reports": 10.0,
    "sec_filing": 10.0,
    "nse_filings": 10.0,
    "bse_filings": 10.0,
    "institutional_documents": 9.5,
    "conference_call": 9.0,
    "investor_presentation": 8.0,
    "reuters": 8.0,
    "bloomberg": 8.0,
    "knowledge_factory": 8.0,
    "ieri": 7.5,
    "research_office": 7.0,
    "ceo_interview": 6.0,
    "news": 5.0,
    "twitter": 2.0,
    "unknown": 4.0,
}
