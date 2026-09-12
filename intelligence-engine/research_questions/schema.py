"""Institutional Research Question Engine (IRQ) V1 — RQ2 Sprint 2."""

from __future__ import annotations

from typing import Any

IRQ_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Hypothesis Intelligence"
PROGRAMME_SHORT = "IRQ"
SPRINT = 2
SPRINT_NAME = "Institutional Research Question Engine (IRQ) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.55
MAX_GENERATION_MS_TARGET = 40
MIN_QUESTIONS_PER_HYPOTHESIS = 10
MAX_QUESTIONS_PER_HYPOTHESIS = 30
MIN_CONTRADICTION_QUESTIONS = 3
MIN_HISTORICAL_QUESTIONS = 2
MIN_PEER_QUESTIONS = 2
BENCHMARK_HYPOTHESIS_SETS = 500
BENCHMARK_MIN_QUESTIONS = 10_000

QUESTION_TYPES: tuple[str, ...] = (
    "Verification",
    "Contradiction",
    "Historical",
    "Peer",
    "Macro",
    "Accounting",
    "Business",
    "Financial",
    "Management",
    "Valuation",
    "Portfolio",
    "Forecast",
    "Risk",
)

QUESTION_PRIORITIES: tuple[str, ...] = (
    "Critical",
    "Important",
    "Supporting",
    "Optional",
)

QUESTION_STATUSES: tuple[str, ...] = (
    "Waiting",
    "Researching",
    "Answered",
    "Evidence Weak",
    "Rejected",
    "Contradicted",
)

QUALITY_RULES: tuple[str, ...] = (
    "specific",
    "answerable",
    "evidence_backed",
    "decision_relevant",
    "non_overlapping",
)

# Logical proof chain order for question trees
TREE_LAYER_ORDER: tuple[str, ...] = (
    "Historical",
    "Peer",
    "Valuation",
    "Forecast",
)

MANDATORY_QUESTION_FIELDS: tuple[str, ...] = (
    "id",
    "question",
    "type",
    "priority",
    "analyst_owner",
    "required_evidence",
    "dependencies",
    "status",
    "confidence",
    "decision_impact",
    "hypothesis_id",
)

PRIMARY_QUESTION = (
    "What questions must be answered before this hypothesis can be accepted?"
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "irq-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IRQ_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "IHG / Hypothesis Generation",
        "executes_before": "Evidence Collection",
        "primary_question": PRIMARY_QUESTION,
        "law": (
            "No hypothesis may proceed to evidence collection until its research questions "
            "have been generated. Analysts answer defined institutional questions — they do not "
            "research everything."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_generation_ms_target": MAX_GENERATION_MS_TARGET,
        "question_types": list(QUESTION_TYPES),
        "priorities": list(QUESTION_PRIORITIES),
        "statuses": list(QUESTION_STATUSES),
        "quality_rules": list(QUALITY_RULES),
        "tree_layer_order": list(TREE_LAYER_ORDER),
        "coverage_rules": {
            "min_questions_per_hypothesis": MIN_QUESTIONS_PER_HYPOTHESIS,
            "max_questions_per_hypothesis": MAX_QUESTIONS_PER_HYPOTHESIS,
            "min_contradiction": MIN_CONTRADICTION_QUESTIONS,
            "min_historical": MIN_HISTORICAL_QUESTIONS,
            "min_peer": MIN_PEER_QUESTIONS,
            "no_duplicates": True,
            "no_generics": True,
        },
        "benchmark": {
            "min_hypothesis_sets": BENCHMARK_HYPOTHESIS_SETS,
            "min_research_questions": BENCHMARK_MIN_QUESTIONS,
        },
        "success_criteria": {
            "question_relevance": 1.0,
            "question_quality": 1.0,
            "question_uniqueness": 1.0,
            "evidence_mapping": 1.0,
            "analyst_ownership": 1.0,
            "coverage": 1.0,
        },
        "enhancements": {
            "question_tree": True,
            "decision_impact_score": True,
        },
    }


IRQ_CONSTITUTION: dict[str, Any] = constitution_dict()
