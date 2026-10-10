"""Institutional Validation & Clarification Engine (IVCE) V1 — RQ1 Sprint 9."""

from __future__ import annotations

from typing import Any

IVCE_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "IVCE"
SPRINT = 9
SPRINT_NAME = "Institutional Validation & Clarification Engine (IVCE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.85
MAX_VALIDATION_MS_TARGET = 15

READINESS_WEIGHTS: dict[str, float] = {
    "question": 0.15,
    "entity": 0.15,
    "intent": 0.15,
    "context": 0.10,
    "evidence": 0.20,
    "routing": 0.10,
    "blueprint": 0.10,
    "policy": 0.05,
}

READINESS_STATES: tuple[str, ...] = (
    "READY",
    "READY_WITH_WARNINGS",
    "CLARIFICATION_REQUIRED",
    "BLOCKED",
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question_status",
    "entity_status",
    "intent_status",
    "context_status",
    "evidence_status",
    "routing_status",
    "blueprint_status",
    "policy_status",
    "overall_readiness",
    "readiness_state",
    "warnings",
    "clarifications",
    "confidence",
    "execution_allowed",
    "readiness_memo",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "ivce-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IVCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "extends": "Entity Resolution / Research Objective / Analyst Router / Layer Router / Blueprint",
        "primary_question": (
            "Is this request sufficiently understood and supported to begin institutional research?"
        ),
        "law": (
            "No institutional research begins until the request has passed all validation gates. "
            "Every Ask AGI request receives an explicit Institutional Readiness Score first."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_validation_ms_target": MAX_VALIDATION_MS_TARGET,
        "readiness_weights": dict(READINESS_WEIGHTS),
        "readiness_states": list(READINESS_STATES),
        "research_readiness_memo": True,
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "success_criteria": {
            "validation_accuracy": 0.99,
            "clarification_accuracy": 0.99,
            "false_ready_rate": 0.01,
            "false_block_rate": 0.01,
            "average_runtime_ms": MAX_VALIDATION_MS_TARGET,
            "benchmark_minimum": 1000,
        },
    }


IVCE_CONSTITUTION: dict[str, Any] = constitution_dict()
