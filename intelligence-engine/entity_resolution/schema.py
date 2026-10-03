"""ERE V1 — RQ1 Sprint 2 schema / constitution constants."""

from __future__ import annotations

from typing import Any

ERE_VERSION = "1.0.0"
PROGRAMME = "RQ1 Entity Resolution Engine"
PROGRAMME_SHORT = "ERE"
SPRINT = 2
SPRINT_NAME = "Entity Resolution Engine"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
PRIMARY_QUESTION = "What is the canonical institutional entity?"
CONFIDENCE_THRESHOLD = 0.85
MAX_RESOLUTION_MS_TARGET = 20

ENTITY_TYPES: tuple[str, ...] = (
    "Company",
    "Sector",
    "Industry",
    "Sector Index",
    "Broad Index",
    "ETF",
    "Mutual Fund",
    "Commodity",
    "Currency",
    "Bond",
    "Country",
    "Macro Variable",
    "Economic Indicator",
    "Portfolio",
    "Watchlist",
    "Theme",
    "Person",
    "Institution",
    "Government",
    "Event",
    "Regulation",
    "Financial Metric",
    "Accounting Metric",
    "Framework",
    "Unknown",
)

CANONICAL_FIELDS: tuple[str, ...] = (
    "id",
    "canonical_name",
    "entity_type",
    "ticker",
    "exchange",
    "country",
    "sector",
    "industry",
    "aliases",
    "status",
    "confidence",
    "parent",
    "children",
    "knowledge_graph_id",
)

OUTPUT_FIELDS: tuple[str, ...] = (
    "entity",
    "entity_type",
    "ticker",
    "exchange",
    "country",
    "sector",
    "industry",
    "confidence",
    "needs_clarification",
    "possible_matches",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": ERE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "law": "Never guess. No research begins until a canonical institutional entity exists.",
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "entity_types": list(ENTITY_TYPES),
        "canonical_fields": list(CANONICAL_FIELDS),
        "output_fields": list(OUTPUT_FIELDS),
        "source_of_truth": "Institutional Knowledge Graph (IKG) with ERE registry soft fallback",
        "not_a_top_level_intelligence_layer": True,
        "no_analyst_execution": True,
        "no_intelligence_layer_execution": True,
    }
