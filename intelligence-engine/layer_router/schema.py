"""Intelligence Layer Router (ILR) V1 — RQ1 Sprint 6 constitution."""

from __future__ import annotations

from typing import Any

ILR_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "ILR"
SPRINT = 6
SPRINT_NAME = "Intelligence Layer Router (ILR) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.85
MAX_PLANNING_MS_TARGET = 30
SUPPRESSION_IMPORTANCE_THRESHOLD = 40  # below → suppress unless required

REGISTERED_LAYERS: tuple[str, ...] = (
    "FIL",
    "FDI",
    "MII",
    "ACI",
    "EIL",
    "PIL",
    "CIG",
    "IKG",
    "FIE",
    "ILM",
    "SSL",
    "Business",
    "Financial",
    "Valuation",
    "Risk",
    "Sector",
    "Macro",
    "Management",
    "Ownership",
    "Portfolio",
    "Committee",
    "IDE V2",
    "CIO",
    "Research Writer",
)

EXECUTION_MODES: tuple[str, ...] = ("Required", "Optional", "Conditional", "Suppressed")

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question",
    "primary_objective",
    "required_layers",
    "optional_layers",
    "suppressed_layers",
    "execution_graph",
    "parallel_groups",
    "dependencies",
    "estimated_runtime",
    "expected_cost",
    "confidence_plan",
    "expected_contributions",
    "executed_layers",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ILR_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "extends": "Research Objective Engine / Analyst Router / Context Intelligence",
        "primary_question": "What intelligence pipeline should execute?",
        "law": (
            "No intelligence layer runs automatically. "
            "Execute only the minimum set required for institutional quality."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_planning_ms_target": MAX_PLANNING_MS_TARGET,
        "suppression_importance_threshold": SUPPRESSION_IMPORTANCE_THRESHOLD,
        "registered_layers": list(REGISTERED_LAYERS),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "expected_contribution_scoring": True,
        "success_criteria": {
            "layer_routing_accuracy": 0.99,
            "dependency_accuracy": 1.0,
            "parallel_execution_accuracy": 0.95,
            "suppressed_layer_accuracy": 0.98,
            "average_planning_ms": MAX_PLANNING_MS_TARGET,
            "average_runtime_reduction": 0.25,
            "benchmark_minimum": 1000,
        },
    }
