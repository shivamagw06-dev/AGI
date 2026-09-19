"""IERE — Institutional Evidence Retrieval Engine schemas."""

from __future__ import annotations

from typing import Any

IERE_VERSION = "institutional-evidence-retrieval-v1.0.0"
PROGRAMME = "AGIB v3.2 – Institutional Evidence Retrieval Engine"
MODULE_CODE = "IERE"

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "governance": True,
    "committees": True,
    "planner": True,
    "reasoning": True,
    "knowledge_factory": True,
    "institutional_documents": True,
    "no_new_intelligence_domains": True,
    "soft_wire_only": True,
    "never_raw_api": True,
    "never_pdf_to_reasoning": True,
    "deterministic_ranking_only": True,
}

EVIDENCE_TYPES: tuple[str, ...] = (
    "FINANCIAL_METRICS",
    "CORPORATE_EVENTS",
    "GOVERNMENT_POLICIES",
    "MACRO_INDICATORS",
    "ALTERNATIVE_DATA",
    "RELATIONSHIP_GRAPH",
    "DOCUMENT_SECTIONS",
    "ACCOUNTING_NOTES",
    "RISK_FACTORS",
    "MANAGEMENT_COMMENTARY",
    "CONFERENCE_CALLS",
    "INVESTOR_PRESENTATIONS",
    "HISTORICAL_VALUATION",
    "OWNERSHIP",
    "TIMELINES",
)

PACK_KINDS: tuple[str, ...] = (
    "COMPANY_EVIDENCE_PACK",
    "INDUSTRY_EVIDENCE_PACK",
    "MACRO_EVIDENCE_PACK",
    "GOVERNMENT_EVIDENCE_PACK",
    "DOCUMENT_EVIDENCE_PACK",
    "HISTORICAL_EVIDENCE_PACK",
    "PORTFOLIO_EVIDENCE_PACK",
    "CROSS_DOMAIN_EVIDENCE_PACK",
)

# Deterministic ranking weights (sum ≈ 1.0)
RANK_WEIGHTS: dict[str, float] = {
    "relevance": 0.22,
    "freshness": 0.12,
    "confidence": 0.12,
    "provenance_quality": 0.14,
    "official_source": 0.10,
    "point_in_time_match": 0.10,
    "coverage": 0.08,
    "completeness": 0.06,
    "consistency": 0.06,
}

OFFICIAL_SOURCE_BONUS = {
    "COMPANY_IR": 1.0,
    "NSE": 1.0,
    "NSE_FILINGS": 1.0,
    "BSE": 0.95,
    "BSE_FILINGS": 0.95,
    "RBI": 1.0,
    "SEBI": 1.0,
    "MCA": 0.9,
    "knowledge_factory": 0.85,
    "institutional_documents": 0.95,
    "live_data": 0.9,
    "research_office": 0.8,
    "seed": 0.55,
    "fixture": 0.4,
}
