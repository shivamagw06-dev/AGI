"""Institutional Acquisition & API Planning Engine (IAPE) V1 — RQ1 Sprint 7."""

from __future__ import annotations

from typing import Any

IAPE_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "IAPE"
SPRINT = 7
SPRINT_NAME = "Institutional Acquisition & API Planning Engine (IAPE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.85
MAX_PLANNING_MS_TARGET = 20

AUTHORITY_TIERS: dict[int, str] = {
    1: "Official — Company / Exchange / Government",
    2: "Regulated Market Data",
    3: "Institutional Research / Broker / Academic",
    4: "News",
    5: "Community / Social Media",
}

FRESHNESS_LEVELS: tuple[str, ...] = (
    "Live",
    "Intraday",
    "Daily",
    "Weekly",
    "Quarterly",
    "Existing knowledge",
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question",
    "required_data",
    "selected_providers",
    "reuse_internal_layers",
    "skipped_apis",
    "fallback_providers",
    "evidence_budget",
    "expected_runtime",
    "expected_quality",
    "freshness_plan",
    "authority_plan",
    "confidence",
    "executed_acquisitions",
)


DEFAULT_EVIDENCE_BUDGET: dict[str, Any] = {
    "maximum_runtime_ms": 4000,
    "maximum_api_calls": 8,
    "target_confidence": 0.90,
    "minimum_authority_tier": 2,
    "required_freshness": "intraday",
}


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "iape-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IAPE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "extends": "Research Objective / Layer Router / Context Intelligence",
        "primary_question": "What evidence must be acquired to answer this question?",
        "law": (
            "Every API call must have a reason. "
            "Acquire only the minimum evidence required for institutional quality."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_planning_ms_target": MAX_PLANNING_MS_TARGET,
        "authority_tiers": AUTHORITY_TIERS,
        "evidence_budget": True,
        "default_evidence_budget": dict(DEFAULT_EVIDENCE_BUDGET),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "success_criteria": {
            "provider_selection_accuracy": 0.99,
            "internal_reuse_accuracy": 1.0,
            "duplicate_api_calls": 0,
            "authority_compliance": 1.0,
            "fallback_success": 0.99,
            "average_planning_ms": MAX_PLANNING_MS_TARGET,
            "average_api_reduction": 0.30,
            "benchmark_minimum": 1000,
        },
    }


IAPE_CONSTITUTION: dict[str, Any] = constitution_dict()
