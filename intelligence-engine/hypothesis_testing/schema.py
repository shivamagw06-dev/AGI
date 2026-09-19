"""Institutional Hypothesis Testing Engine (IHTE) V1 — RQ2 Sprint 4."""

from __future__ import annotations

from typing import Any

IHTE_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Hypothesis Intelligence"
PROGRAMME_SHORT = "IHTE"
SPRINT = 4
SPRINT_NAME = "Institutional Hypothesis Testing Engine (IHTE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.55
MAX_TESTING_MS_TARGET = 50
BENCHMARK_MIN_TESTED_HYPOTHESES = 10_000

MIN_SUPPORTING_EVIDENCE = 5
MIN_CONTRADICTORY_EVIDENCE = 2
MIN_HISTORICAL_EVIDENCE = 1
MIN_PEER_EVIDENCE = 1
MIN_MACRO_EVIDENCE = 1

HYPOTHESIS_STATUSES: tuple[str, ...] = (
    "Supported",
    "Partially Supported",
    "Inconclusive",
    "Contradicted",
    "Rejected",
)

EVIDENCE_EFFECTS: tuple[str, ...] = (
    "Confirms",
    "Supports",
    "Weakly Supports",
    "Neutral",
    "Questions",
    "Contradicts",
    "Refutes",
)

# Probability deltas by qualitative effect (percentage points)
EFFECT_DELTAS: dict[str, float] = {
    "Confirms": 0.12,
    "Supports": 0.07,
    "Weakly Supports": 0.03,
    "Neutral": 0.0,
    "Questions": -0.05,
    "Contradicts": -0.09,
    "Refutes": -0.18,
}

PRIMARY_QUESTION = (
    "Does the available evidence strengthen, weaken or invalidate this hypothesis?"
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "hypothesis",
    "initial_confidence",
    "support_score",
    "contradiction_score",
    "missing_evidence",
    "updated_probability",
    "status",
    "assumptions",
    "uncertainty",
    "confidence",
    "evidence_effects",
    "reasoning_ledger",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "ihte-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IHTE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Evidence Planning",
        "executes_before": "Business / Financial / Valuation Analysts",
        "primary_question": PRIMARY_QUESTION,
        "law": (
            "No analyst may form an opinion until every assigned hypothesis has completed "
            "institutional testing. Analysts receive tested hypotheses instead of raw evidence."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_testing_ms_target": MAX_TESTING_MS_TARGET,
        "statuses": list(HYPOTHESIS_STATUSES),
        "evidence_effects": list(EVIDENCE_EFFECTS),
        "effect_deltas": dict(EFFECT_DELTAS),
        "quality_rules": {
            "min_supporting_evidence": MIN_SUPPORTING_EVIDENCE,
            "min_contradictory_evidence": MIN_CONTRADICTORY_EVIDENCE,
            "min_historical_evidence": MIN_HISTORICAL_EVIDENCE,
            "min_peer_evidence": MIN_PEER_EVIDENCE,
            "min_macro_evidence": MIN_MACRO_EVIDENCE,
        },
        "benchmark": {"min_tested_hypotheses": BENCHMARK_MIN_TESTED_HYPOTHESES},
        "enhancements": {
            "qualitative_evidence_effects": True,
            "reasoning_ledger": True,
        },
        "success_criteria": {
            "evidence_attribution": 1.0,
            "support_scoring": 1.0,
            "contradiction_scoring": 1.0,
            "probability_updates": 1.0,
            "uncertainty_reporting": 1.0,
        },
    }


IHTE_CONSTITUTION: dict[str, Any] = constitution_dict()
