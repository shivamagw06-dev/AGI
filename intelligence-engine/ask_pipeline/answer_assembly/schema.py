"""AGIB v3.4 Track B — Institutional Answer Assembly Engine schemas."""

from __future__ import annotations

from typing import Any

AAE_VERSION = "answer-assembly-v1.0.0"
PROGRAMME = "AGIB v3.4 – Institutional Answer Excellence · Track B Answer Assembly"
MODULE_CODE = "AAE"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "governance_internals": True,
    "committees": True,
    "no_llm_ranking": True,
    "no_llm_synthesis": True,
    "deterministic_only": True,
    "soft_wire_only": True,
    "reasoning_frozen": True,
    "no_new_intelligence_domains": True,
}

EVIDENCE_DOMAINS: tuple[str, ...] = (
    "Financial",
    "Accounting",
    "BusinessModel",
    "ValuationFramework",
    "Historical",
    "Macro",
    "Government",
    "Industry",
    "Documents",
    "AlternativeData",
    "CorporateEvents",
    "Ownership",
    "Risk",
    "Relationships",
    "Other",
)

SKELETON_SECTIONS: tuple[str, ...] = (
    "executive_summary",
    "evidence",
    "analysis",
    "framework",
    "risks",
    "conclusion",
    "confidence",
    "sources",
)

# Intent → preferred evidence domain order (Stage 2 importance)
DOMAIN_PRIORITY: dict[str, tuple[str, ...]] = {
    "Explain": (
        "Accounting",
        "BusinessModel",
        "ValuationFramework",
        "Historical",
        "Financial",
        "Industry",
        "Documents",
        "Macro",
        "Government",
        "Risk",
    ),
    "Education": (
        "ValuationFramework",
        "Accounting",
        "BusinessModel",
        "Financial",
        "Historical",
        "Documents",
    ),
    "Compare": (
        "Financial",
        "Historical",
        "Industry",
        "Ownership",
        "Relationships",
        "Documents",
        "ValuationFramework",
    ),
    "Analyse": (
        "Financial",
        "Accounting",
        "Documents",
        "CorporateEvents",
        "Historical",
        "Risk",
        "Industry",
    ),
    "Valuation": (
        "ValuationFramework",
        "Financial",
        "Historical",
        "Ownership",
        "Industry",
        "Documents",
    ),
    "Industry": (
        "Industry",
        "Relationships",
        "Macro",
        "Financial",
        "Government",
        "Historical",
    ),
    "Macro": (
        "Macro",
        "Government",
        "Industry",
        "AlternativeData",
        "Financial",
        "Historical",
    ),
    "Government": (
        "Government",
        "Macro",
        "Industry",
        "Relationships",
        "AlternativeData",
    ),
    "Documents": (
        "Documents",
        "Risk",
        "Accounting",
        "BusinessModel",
        "Financial",
        "Ownership",
    ),
    "HistoricalReplay": (
        "Historical",
        "Documents",
        "Financial",
        "CorporateEvents",
        "Risk",
    ),
    "CrossDomain": (
        "Macro",
        "Government",
        "Industry",
        "AlternativeData",
        "Financial",
        "Historical",
        "Documents",
        "CorporateEvents",
    ),
    "Accounting": ("Accounting", "Financial", "Documents", "Historical", "Risk"),
    "Risk": ("Risk", "Documents", "Macro", "Financial", "CorporateEvents"),
    "CorporateEvents": ("CorporateEvents", "Documents", "Financial", "Historical"),
    "Portfolio": ("Financial", "Ownership", "Risk", "Industry", "Macro"),
    "Unknown": ("Financial", "Documents", "Industry", "Macro", "Historical"),
}

# Map IERE evidence_type → domain
TYPE_TO_DOMAIN: dict[str, str] = {
    "FINANCIAL_METRICS": "Financial",
    "HISTORICAL_VALUATION": "Historical",
    "MACRO_INDICATORS": "Macro",
    "GOVERNMENT_POLICIES": "Government",
    "RELATIONSHIP_GRAPH": "Industry",
    "DOCUMENT_SECTIONS": "Documents",
    "ACCOUNTING_NOTES": "Accounting",
    "RISK_FACTORS": "Risk",
    "MANAGEMENT_COMMENTARY": "Documents",
    "CONFERENCE_CALLS": "Documents",
    "INVESTOR_PRESENTATIONS": "Documents",
    "ALTERNATIVE_DATA": "AlternativeData",
    "CORPORATE_EVENTS": "CorporateEvents",
    "OWNERSHIP": "Ownership",
    "TIMELINES": "Historical",
}

CONFIDENCE_BANDS: tuple[tuple[float, str], ...] = (
    (0.85, "High"),
    (0.65, "Moderate"),
    (0.40, "Low"),
    (0.0, "Insufficient"),
)
