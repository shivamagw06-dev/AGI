"""Institutional Corporate Event Intelligence (ICEI) — AGIB v2.0 Sprint 2.

Soft Knowledge Factory enrichment only.
Phases 1–7, KF architecture, Company Intelligence, Decision Quality: FROZEN.
Never invent events. Point-in-time replay must exclude future events.
"""

from __future__ import annotations

from typing import Any

ICEI_VERSION = "institutional-corporate-event-intelligence-v2.0.0"
ICEI_SCHEMA_VERSION = "icei-schema-v2.0.0"
PROGRAMME = "AGIB v2.0 – Institutional Corporate Event Intelligence"
LAYER = "ICEI"
ARCHITECTURE_STATUS = "SOFT_CORPORATE_EVENT_INTELLIGENCE"

SEVERITIES: tuple[str, ...] = (
    "Critical",
    "High",
    "Medium",
    "Low",
    "Informational",
)

CATEGORIES: dict[str, tuple[str, ...]] = {
    "financial": (
        "quarterly_results",
        "annual_results",
        "guidance",
        "revenue_revision",
        "margin_guidance",
        "ebitda_revision",
        "capex_guidance",
    ),
    "capital_allocation": (
        "dividend",
        "buyback",
        "rights_issue",
        "bonus",
        "stock_split",
        "qip",
        "ofs",
        "preferential_issue",
    ),
    "corporate_structure": (
        "acquisition",
        "disposal",
        "merger",
        "demerger",
        "jv",
        "subsidiary",
        "ipo",
        "incorporation",
        "listing",
    ),
    "management": (
        "ceo_appointment",
        "ceo_resignation",
        "ceo_change",
        "cfo",
        "chairman",
        "board",
        "independent_director",
        "auditor",
    ),
    "operations": (
        "new_plant",
        "capacity_expansion",
        "shutdown",
        "production_start",
        "major_contract",
        "export_order",
        "tender",
        "strategy",
    ),
    "regulatory": (
        "sebi",
        "rbi",
        "nclt",
        "cci",
        "court_order",
        "environmental_approval",
        "government_approval",
        "regulatory",
    ),
    "credit": (
        "upgrade",
        "downgrade",
        "watchlist",
        "outlook",
    ),
    "shareholding": (
        "promoter_increase",
        "promoter_sale",
        "pledge",
        "fii",
        "dii",
        "insider_buying",
        "insider_selling",
    ),
    "legal": (
        "litigation",
        "tax_notice",
        "arbitration",
        "penalty",
    ),
    "esg": (
        "sustainability",
        "carbon",
        "csr",
        "safety",
        "governance",
    ),
    "macro_context": (
        "covid",
        "global_event",
    ),
}

TYPE_TO_CATEGORY: dict[str, str] = {
    t: cat for cat, types in CATEGORIES.items() for t in types
}

# Alias map from soft upstream event_type strings
TYPE_ALIASES: dict[str, str] = {
    "earnings": "quarterly_results",
    "results": "quarterly_results",
    "capital_raise": "qip",
    "ceo_change": "ceo_change",
    "corporate_action": "dividend",
}

IMPACT_DIMENSIONS: tuple[str, ...] = (
    "earnings",
    "margin",
    "cash_flow",
    "balance_sheet",
    "growth",
    "risk",
)

IMPACT_VALUES: tuple[str, ...] = (
    "positive",
    "negative",
    "mixed",
    "neutral",
    "unknown",
    "not_applicable",
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "knowledge_factory_architecture": True,
    "company_intelligence_architecture": True,
    "universe_intelligence_architecture": True,
    "decision_quality_architecture": True,
    "governance": True,
    "committees": True,
    "planner": True,
    "evidence_contracts": True,
    "framework_execution": True,
    "learning_engine": True,
    "not_a_reasoning_engine": True,
    "never_invent_events": True,
    "point_in_time_integrity": True,
    "immutable_timelines": True,
}


def canonicalize_type(event_type: str) -> str:
    t = str(event_type or "").strip().lower().replace(" ", "_").replace("-", "_")
    return TYPE_ALIASES.get(t, t)


def category_for(event_type: str) -> str:
    t = canonicalize_type(event_type)
    return TYPE_TO_CATEGORY.get(t, "operations")


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "icei_version": ICEI_VERSION,
        "icei_schema_version": ICEI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "kind": kind,
        "architecture_status": ARCHITECTURE_STATUS,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        **extra,
        **payload,
    }
