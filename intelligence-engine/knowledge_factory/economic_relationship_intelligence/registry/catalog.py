"""Relationship Registry — types, semantics, entity kinds."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence.schema import (
    ECONOMIC_SEMANTICS,
    ENTITY_KINDS,
    IERI_VERSION,
    RELATIONSHIP_TYPES,
    TYPE_TO_SEMANTICS,
)

RELATIONSHIP_REGISTRY: dict[str, Any] = {
    "version": IERI_VERSION,
    "relationship_types": list(RELATIONSHIP_TYPES),
    "economic_semantics": list(ECONOMIC_SEMANTICS),
    "entity_kinds": list(ENTITY_KINDS),
    "type_to_semantics": dict(TYPE_TO_SEMANTICS),
    "data_source_priority": [
        "annual_reports",
        "investor_presentations",
        "company_websites",
        "nse_filings",
        "bse_filings",
        "government_publications",
        "rbi",
        "sebi",
        "ministry_reports",
        "industry_associations",
        "public_trade_statistics",
        "official_commodity_data",
    ],
}


def registry_snapshot() -> dict[str, Any]:
    return dict(RELATIONSHIP_REGISTRY)
