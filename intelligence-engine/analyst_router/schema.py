"""Institutional Analyst Router (IAR) V1 — RQ1 Sprint 5 constitution."""

from __future__ import annotations

from typing import Any

IAR_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "IAR"
SPRINT = 5
SPRINT_NAME = "Institutional Analyst Router (IAR) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.85
MAX_ROUTING_MS_TARGET = 30

# Canonical registry (product-facing Title Case)
ANALYST_REGISTRY: tuple[str, ...] = (
    "Business",
    "Financial",
    "Valuation",
    "Risk",
    "Sector",
    "Macro",
    "Management",
    "Ownership",
    "Accounting",
    "Portfolio",
    "Forecast",
    "Market",
    "News",
    "Academy",
    "Committee",
    "CIO",
)

# Roles that may vote in committee synthesis
VOTING_ANALYSTS: frozenset[str] = frozenset(
    {
        "Business",
        "Financial",
        "Valuation",
        "Risk",
        "Sector",
        "Macro",
        "Portfolio",
        "Forecast",
        "Committee",
        "CIO",
    }
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question",
    "primary_objective",
    "required_analysts",
    "optional_analysts",
    "suppressed_analysts",
    "speaking_order",
    "weights",
    "dependencies",
    "assignments",
    "routing_confidence",
    "executed_analysts",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IAR_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "extends": "Research Objective Engine / Intent Intelligence",
        "primary_question": "Which institutional specialists are required to answer this question?",
        "law": (
            "Institutional research is not democracy. "
            "Only relevant specialists participate; suppressed analysts must not execute."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_routing_ms_target": MAX_ROUTING_MS_TARGET,
        "analyst_registry": list(ANALYST_REGISTRY),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "success_criteria": {
            "analyst_selection_accuracy": 0.98,
            "exclusion_accuracy": 0.98,
            "speaking_order_accuracy": 0.98,
            "weight_accuracy": 0.98,
            "mandate_violations": 0,
            "benchmark_minimum": 1000,
            "average_routing_ms": MAX_ROUTING_MS_TARGET,
        },
    }
