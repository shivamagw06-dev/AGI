"""Institutional Hypothesis Generation Engine (IHG) V1 — RQ2 Sprint 1."""

from __future__ import annotations

from typing import Any

IHG_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Hypothesis Intelligence"
PROGRAMME_SHORT = "IHG"
SPRINT = 1
SPRINT_NAME = "Institutional Hypothesis Generation Engine (IHG) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.55
MAX_GENERATION_MS_TARGET = 30

HYPOTHESIS_TYPES: tuple[str, ...] = (
    "Business",
    "Financial",
    "Valuation",
    "Macro",
    "Risk",
    "Portfolio",
    "Management",
    "Accounting",
    "Industry",
    "Competitive",
    "Capital Allocation",
    "Forecast",
)

HYPOTHESIS_STATUSES: tuple[str, ...] = (
    "proposed",
    "under_investigation",
    "supported",
    "challenged",
    "disproven",
    "inconclusive",
)

QUALITY_RULES: tuple[str, ...] = (
    "specific",
    "testable",
    "falsifiable",
    "evidence_required",
    "decision_relevant",
)

MANDATORY_HYPOTHESIS_FIELDS: tuple[str, ...] = (
    "id",
    "statement",
    "reason",
    "type",
    "confidence",
    "required_evidence",
    "responsible_analysts",
    "priority",
    "status",
    "assumptions",
    "quality_rules",
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question",
    "hypotheses",
    "ranking",
    "evidence_map",
    "contradictions",
    "overall_confidence",
    "generation_ms",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "ihg-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IHG_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "IREP",
        "executes_before": "First analyst research",
        "primary_question": (
            "What are the most plausible explanations or investment theses that should be tested?"
        ),
        "law": (
            "Institutional analysts begin by generating hypotheses that must be proven or disproven. "
            "Every hypothesis must be specific, testable, falsifiable, evidence-required, and decision-relevant."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_generation_ms_target": MAX_GENERATION_MS_TARGET,
        "hypothesis_types": list(HYPOTHESIS_TYPES),
        "quality_rules": list(QUALITY_RULES),
        "mandatory_hypothesis_fields": list(MANDATORY_HYPOTHESIS_FIELDS),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "success_criteria": {
            "hypothesis_generation_coverage": 1.0,
            "quality_rule_compliance": 1.0,
            "no_generic_hypotheses": 1.0,
            "ranking_consistency": 0.99,
            "average_generation_ms": MAX_GENERATION_MS_TARGET,
            "benchmark_minimum": 1000,
        },
    }


IHG_CONSTITUTION: dict[str, Any] = constitution_dict()
