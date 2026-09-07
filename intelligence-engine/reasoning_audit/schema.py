"""Institutional Reasoning Audit Engine (IRAE) V1 — RQ2 Sprint 10."""

from __future__ import annotations

from typing import Any

IRAE_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Institutional Reasoning"
PROGRAMME_SHORT = "IRAE"
SPRINT = 10
SPRINT_NAME = "Institutional Reasoning Audit Engine (IRAE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
MAX_AUDIT_MS_TARGET = 75
BENCHMARK_MIN_CHAINS = 10_000

AUDIT_DIMENSIONS: tuple[str, ...] = (
    "Evidence Traceability",
    "Logical Consistency",
    "Assumption Quality",
    "Contradiction Handling",
    "Confidence Calibration",
    "Policy Compliance",
    "Analyst Scope",
    "Reasoning Completeness",
)

AUDIT_WEIGHTS: dict[str, float] = {
    "Evidence Traceability": 0.20,
    "Logical Consistency": 0.16,
    "Assumption Quality": 0.11,
    "Contradiction Handling": 0.13,
    "Confidence Calibration": 0.12,
    "Policy Compliance": 0.12,
    "Analyst Scope": 0.07,
    "Reasoning Completeness": 0.09,
}

AUDIT_STATES: tuple[str, ...] = (
    "PASS",
    "PASS WITH OBSERVATIONS",
    "REVIEW REQUIRED",
    "FAIL",
)

REASONING_STAGES: tuple[str, ...] = (
    "Question",
    "Hypothesis",
    "Research Questions",
    "Evidence",
    "Testing",
    "Falsification",
    "Belief Update",
    "Investment Thesis",
    "Debate",
    "Decision Readiness",
    "Reasoning Audit",
)

CHAIN_TYPES: tuple[str, ...] = (
    "Equity",
    "Portfolio",
    "Macro",
    "Sector",
    "Comparative",
    "Forecast",
)

PRIMARY_QUESTION = "Did AGIB reason correctly?"


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "irae-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IRAE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "final_reasoning_certification_gate": True,
        "executes_after": "Institutional Decision Readiness Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "law": (
            "Only audited reasoning may proceed. Every conclusion must have an unbroken, "
            "reproducible chain from question to decision readiness."
        ),
        "dimensions": list(AUDIT_DIMENSIONS),
        "weights": dict(AUDIT_WEIGHTS),
        "states": list(AUDIT_STATES),
        "reasoning_stages": list(REASONING_STAGES),
        "quality_rules": {
            "traceability": 1.0,
            "unsupported_conclusions": 0,
            "critical_policy_issues": 0,
            "analyst_scope_violations": 0,
            "contradictions_disclosed": 1.0,
            "confidence_calibrated": 1.0,
        },
        "benchmark": {
            "min_reasoning_chains": BENCHMARK_MIN_CHAINS,
            "chain_types": list(CHAIN_TYPES),
        },
        "extensions": {
            "reasoning_replay_engine": True,
            "step_by_step_replay": True,
        },
    }
