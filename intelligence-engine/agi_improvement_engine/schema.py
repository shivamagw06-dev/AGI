"""Frozen contracts for the Ask AGI improvement worker."""

from __future__ import annotations

ENGINE_VERSION = "agi-investment-improvement-v1.0.0"

SCORE_WEIGHTS = {
    "entity_correctness": 15,
    "numerical_accuracy": 20,
    "evidence_support": 20,
    "financial_reasoning": 20,
    "freshness": 10,
    "completeness": 10,
    "communication": 5,
}

FAILURE_TAXONOMY = (
    "ENTITY_FAILURE", "DATA_MISSING", "DATA_STALE", "DATA_CONFLICT",
    "RETRIEVAL_FAILURE", "RANKING_FAILURE", "ROUTING_FAILURE",
    "CALCULATION_ERROR", "VALUATION_FRAMEWORK_ERROR",
    "FINANCIAL_REASONING_ERROR", "CONVERSATION_FAILURE", "CONTEXT_FAILURE",
    "SOURCE_FAILURE", "CITATION_FAILURE", "UNSUPPORTED_CLAIM",
    "OVERCONFIDENCE", "UNDER_SPECIFICATION", "SYSTEM_FAILURE",
    "LATENCY_FAILURE", "MODEL_FAILURE",
)

CRITICAL_FAILURES = (
    "wrong_entity", "invented_number", "invented_source", "material_calculation_error",
    "unsupported_citation", "stale_as_current", "fabricated_information",
    "hidden_material_conflict", "unsupported_certainty",
)

DIFFICULTIES = (
    "LEVEL_1_LOOKUP", "LEVEL_2_CALCULATION", "LEVEL_3_ANALYSIS",
    "LEVEL_4_SYNTHESIS", "LEVEL_5_INSTITUTIONAL",
)

RAMP_STAGES = (100, 250, 500, 1000, 2500)
SAFE_DEFAULT_MAX_QUESTIONS = 100
SAFE_DEFAULT_CONCURRENCY = 2
SAFE_MAX_CONCURRENCY = 8

NORTH_STAR = (
    "A ChatGPT-like conversational interface for Indian investment research that is "
    "financially rigorous, current, evidence-grounded, context-aware and transparent."
)

GOVERNANCE = {
    "model_weight_training": False,
    "self_generated_answers_are_evidence": False,
    "automatic_merge_or_deploy": False,
    "automatic_trading": False,
    "production_schema_mutation": False,
    "raw_secrets_in_logs": False,
    "material_logic_changes_require_review": True,
}
