"""Institutional Economic Relationship Intelligence (IERI) — AGIB v2.0 Sprint 5.

Soft Knowledge Factory enrichment only.
Structured economic relationships — NOT a reasoning engine, planner, or graph DB product.
Graph is an implementation detail; the product is evidence-backed economic knowledge.
Never invent. Unknown remains UNKNOWN.
"""

from __future__ import annotations

from typing import Any

IERI_VERSION = "institutional-economic-relationship-intelligence-v2.0.0"
IERI_SCHEMA_VERSION = "ieri-schema-v2.0.0"
PROGRAMME = "AGIB v2.0 – Institutional Economic Relationship Intelligence"
LAYER = "IERI"
ARCHITECTURE_STATUS = "SOFT_ECONOMIC_RELATIONSHIP_INTELLIGENCE"
UNKNOWN = "UNKNOWN"

# Economic semantics — classification for retrieval / filtering / explanation.
# Not reasoning. Knowledge taxonomy only.
ECONOMIC_SEMANTICS: tuple[str, ...] = (
    "structural",   # supplier, subsidiary, competitor, JV, parent
    "financial",    # ownership, funding, credit exposure
    "policy",       # RBI, GST, PLI, duties, budget
    "market",       # commodity, pricing, demand
    "operational",  # logistics, power, ports, labour
    "behavioural",  # substitutes, complements
)

RELATIONSHIP_TYPES: tuple[str, ...] = (
    "supplier",
    "customer",
    "competitor",
    "distributor",
    "partner",
    "jv",
    "parent",
    "subsidiary",
    "holding_company",
    "promoter",
    "institutional_ownership",
    "commodity_exposure",
    "import_dependency",
    "export_dependency",
    "power_dependency",
    "water_dependency",
    "transport_dependency",
    "logistics_dependency",
    "government_dependency",
    "policy_dependency",
    "interest_rate_sensitivity",
    "inflation_sensitivity",
    "fx_sensitivity",
    "oil_sensitivity",
    "coal_sensitivity",
    "gas_sensitivity",
    "steel_sensitivity",
    "cement_dependency",
    "technology_dependency",
    "labour_dependency",
    "credit_dependency",
    "upstream_industry",
    "downstream_industry",
    "supporting_industry",
    "complementary_industry",
    "substitute_industry",
    "transmission",
)

# Default semantics mapping for relationship types
TYPE_TO_SEMANTICS: dict[str, str] = {
    "supplier": "structural",
    "customer": "structural",
    "competitor": "structural",
    "distributor": "structural",
    "partner": "structural",
    "jv": "structural",
    "parent": "structural",
    "subsidiary": "structural",
    "holding_company": "structural",
    "promoter": "financial",
    "institutional_ownership": "financial",
    "commodity_exposure": "market",
    "import_dependency": "market",
    "export_dependency": "market",
    "power_dependency": "operational",
    "water_dependency": "operational",
    "transport_dependency": "operational",
    "logistics_dependency": "operational",
    "government_dependency": "policy",
    "policy_dependency": "policy",
    "interest_rate_sensitivity": "market",
    "inflation_sensitivity": "market",
    "fx_sensitivity": "market",
    "oil_sensitivity": "market",
    "coal_sensitivity": "market",
    "gas_sensitivity": "market",
    "steel_sensitivity": "market",
    "cement_dependency": "market",
    "technology_dependency": "operational",
    "labour_dependency": "operational",
    "credit_dependency": "financial",
    "upstream_industry": "structural",
    "downstream_industry": "structural",
    "supporting_industry": "structural",
    "complementary_industry": "behavioural",
    "substitute_industry": "behavioural",
    "transmission": "market",
}

DIRECTIONS: tuple[str, ...] = ("outbound", "inbound", "bidirectional", "affects")

ENTITY_KINDS: tuple[str, ...] = (
    "company",
    "industry",
    "commodity",
    "policy",
    "macro",
    "port",
    "railway",
    "utility",
    "bank",
    "government_body",
    "sector",
)

QUALITY_GATES: tuple[str, ...] = (
    "provenance",
    "source",
    "direction",
    "path_integrity",
    "duplicate",
    "relationship_type",
    "semantics",
    "validation",
    "historical_replay",
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
    "industry_value_chain_intelligence_architecture": True,
    "historical_intelligence": True,
    "sector_intelligence_architecture": True,
    "macro_intelligence_architecture": True,
    "knowledge_factory_architecture": True,
    "planner": True,
    "framework_selection": True,
    "learning_engine": True,
    "not_a_reasoning_engine": True,
    "not_a_graph_database_project": True,
    "not_a_planner": True,
    "never_fabricate": True,
    "point_in_time_integrity": True,
    "soft_wire_only": True,
}


def semantics_for(relationship_type: str, override: str | None = None) -> str:
    if override and override in ECONOMIC_SEMANTICS:
        return override
    return TYPE_TO_SEMANTICS.get(str(relationship_type or "").lower(), "structural")


def envelope(*, kind: str, payload: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "ieri_version": IERI_VERSION,
        "ieri_schema_version": IERI_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "kind": kind,
        "architecture_status": ARCHITECTURE_STATUS,
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "reasoning_changed": False,
        **extra,
        **payload,
    }
