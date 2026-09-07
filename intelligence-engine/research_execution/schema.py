"""Institutional Research Execution Package (IREP) V1 — RQ1 Sprint 10."""

from __future__ import annotations

from typing import Any

IREP_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "IREP"
SPRINT = 10
SPRINT_NAME = "Institutional Research Execution Package (IREP) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
ARCHITECTURE_VERSION = "v1.0.1"
RESEARCH_VERSION = "RQ1"
CONFIDENCE_THRESHOLD = 0.85
MAX_PACKAGE_MS_TARGET = 25

MANDATORY_PACKAGE_SECTIONS: tuple[str, ...] = (
    "metadata",
    "question",
    "intent",
    "entity",
    "research_objective",
    "context",
    "analyst_plan",
    "layer_plan",
    "api_plan",
    "blueprint",
    "validation",
    "execution_plan",
    "quality_targets",
    "success_metrics",
    "research_contract",
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "package_id",
    "immutable",
    "metadata",
    "question",
    "intent",
    "entity",
    "research_objective",
    "context",
    "analyst_plan",
    "layer_plan",
    "api_plan",
    "blueprint",
    "validation",
    "execution_plan",
    "quality_targets",
    "success_metrics",
    "research_contract",
    "package_complete",
    "package_consistent",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "irep-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IREP_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "architecture_version": ARCHITECTURE_VERSION,
        "research_version": RESEARCH_VERSION,
        "not_a_top_level_intelligence_layer": True,
        "extends": "RQ1 Sprints 1–9 planning stack",
        "primary_question": "What institutional research package should be executed?",
        "law": (
            "No downstream component independently interprets the user's question. "
            "Every component receives the same institutional understanding. "
            "IREP is immutable once generated."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_package_ms_target": MAX_PACKAGE_MS_TARGET,
        "mandatory_package_sections": list(MANDATORY_PACKAGE_SECTIONS),
        "research_contract": True,
        "package_immutability": True,
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "success_criteria": {
            "package_completeness": 1.0,
            "package_consistency": 1.0,
            "no_conflicting_plans": 1.0,
            "correct_analyst_plan": 0.99,
            "correct_layer_plan": 0.99,
            "correct_blueprint": 0.99,
            "average_package_ms": MAX_PACKAGE_MS_TARGET,
            "benchmark_minimum": 1000,
        },
        "rq1_complete": True,
    }


IREP_CONSTITUTION: dict[str, Any] = constitution_dict()
