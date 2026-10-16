"""Bayesian Belief & Confidence Engine (BBCE) V1 — RQ2 Sprint 6."""

from __future__ import annotations

from typing import Any

BBCE_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Hypothesis Intelligence"
PROGRAMME_SHORT = "BBCE"
SPRINT = 6
SPRINT_NAME = "Bayesian Belief & Confidence Engine (BBCE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.55
MAX_UPDATE_MS_TARGET = 40
BENCHMARK_MIN_BELIEFS = 5_000

BELIEF_STATES: tuple[str, ...] = (
    "Strongly Supported",
    "Supported",
    "Leaning Positive",
    "Neutral",
    "Leaning Negative",
    "Challenged",
    "Contradicted",
    "Rejected",
)

# Log-likelihood ratio contributions by qualitative evidence effect
EFFECT_LOG_LR: dict[str, float] = {
    "Confirms": 1.25,
    "Supports": 0.75,
    "Weakly Supports": 0.35,
    "Neutral": 0.0,
    "Questions": -0.45,
    "Contradicts": -0.9,
    "Refutes": -1.8,
}

# Soft penalties from falsification report severity
FALSIFICATION_LOG_LR: dict[str, float] = {
    "survived": 0.15,
    "stressed": -0.35,
    "weakened": -0.7,
    "falsified": -1.6,
    "inconclusive": -0.1,
}

PRIMARY_QUESTION = (
    "Given all available evidence, what should AGIB currently believe, and how confident should it be?"
)

MANDATORY_BELIEF_FIELDS: tuple[str, ...] = (
    "hypothesis_id",
    "hypothesis",
    "prior_belief",
    "supporting_evidence",
    "contradicting_evidence",
    "posterior_belief",
    "belief_state",
    "confidence",
    "uncertainty",
    "calibration",
    "history",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "bbce-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": BBCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Institutional Falsification Engine",
        "executes_before": "Business / Financial / Valuation opinions",
        "primary_question": PRIMARY_QUESTION,
        "law": (
            "Institutional confidence is not fixed. Confidence evolves as evidence accumulates. "
            "BBCE converts tested and challenged hypotheses into calibrated institutional beliefs."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_update_ms_target": MAX_UPDATE_MS_TARGET,
        "belief_states": list(BELIEF_STATES),
        "effect_log_lr": dict(EFFECT_LOG_LR),
        "falsification_log_lr": dict(FALSIFICATION_LOG_LR),
        "benchmark": {"min_beliefs": BENCHMARK_MIN_BELIEFS},
        "success_criteria": {
            "prior_posterior_consistency": 1.0,
            "belief_state_coverage": 1.0,
            "calibration_reporting": 1.0,
            "history_tracking": 1.0,
            "drift_detection": 1.0,
        },
    }


BBCE_CONSTITUTION: dict[str, Any] = constitution_dict()
