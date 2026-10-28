"""Institutional Industry & Value Chain Intelligence (IIVI) — AGIB v2.0 Sprint 4.

Soft Knowledge Factory enrichment only.
Teaches HOW industries work. Reasoning / governance / prior sprints: FROZEN.
Never fabricate — mark UNKNOWN when unsupported.
"""

from __future__ import annotations

from typing import Any

IIVI_VERSION = "institutional-industry-value-chain-intelligence-v2.0.0"
IIVI_SCHEMA_VERSION = "iivi-schema-v2.0.0"
PROGRAMME = "AGIB v2.0 – Institutional Industry & Value Chain Intelligence"
LAYER = "IIVI"
ARCHITECTURE_STATUS = "SOFT_INDUSTRY_VALUE_CHAIN_INTELLIGENCE"
UNKNOWN = "UNKNOWN"

# Future sprint (declared, not built here)
FUTURE_ECONOMIC_NETWORK_GRAPH = {
    "sprint": "later",
    "name": "Economic Network Graph",
    "purpose": "Company↔supplier/customer/competitor/commodity chain-reaction queries",
    "depends_on": "IIVI",
}

MODULES: tuple[str, ...] = (
    "identity",
    "business_model",
    "value_chain",
    "supply_chain",
    "economics",
    "accounting",
    "valuation",
    "kpis",
    "competition",
    "macro",
    "government",
    "cycles",
    "playbook",
    "knowledge_graph",
)

QUALITY_GATES: tuple[str, ...] = (
    "business_model",
    "value_chain",
    "accounting",
    "kpis",
    "valuation",
    "macro",
    "government",
    "provenance",
    "validation",
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "governance": True,
    "committee_system": True,
    "evidence_contracts": True,
    "decision_quality_architecture": True,
    "universe_intelligence_architecture": True,
    "company_intelligence_architecture": True,
    "corporate_event_intelligence_architecture": True,
    "government_intelligence_architecture": True,
    "historical_intelligence": True,
    "sector_intelligence_architecture": True,
    "macro_intelligence_architecture": True,
    "knowledge_factory_architecture": True,
    "planner": True,
    "framework_selection": True,
    "learning_engine": True,
    "not_a_reasoning_engine": True,
    "never_fabricate": True,
    "point_in_time_integrity": True,
}


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "iivi_version": IIVI_VERSION,
        "iivi_schema_version": IIVI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "kind": kind,
        "architecture_status": ARCHITECTURE_STATUS,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "future_roadmap": FUTURE_ECONOMIC_NETWORK_GRAPH,
        **extra,
        **payload,
    }
