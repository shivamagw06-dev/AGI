"""Institutional Decision Readiness Engine (IDRE) V1 — RQ2 Sprint 9."""

from __future__ import annotations

from typing import Any

IDRE_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Institutional Reasoning"
PROGRAMME_SHORT = "IDRE"
SPRINT = 9
SPRINT_NAME = "Institutional Decision Readiness Engine (IDRE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
MAX_READINESS_MS_TARGET = 60
BENCHMARK_MIN_SCENARIOS = 5_000

READINESS_DIMENSIONS: tuple[str, ...] = (
    "Evidence",
    "Reasoning",
    "Debate",
    "Portfolio",
    "Monitoring",
    "Policy",
    "Confidence",
)

READINESS_WEIGHTS: dict[str, float] = {
    "Evidence": 0.30,
    "Reasoning": 0.20,
    "Debate": 0.15,
    "Portfolio": 0.15,
    "Monitoring": 0.10,
    "Policy": 0.10,
}

READINESS_STATES: tuple[str, ...] = (
    "READY",
    "READY WITH CONDITIONS",
    "RESEARCH REQUIRED",
    "NOT READY",
)

RESEARCH_TYPES: tuple[str, ...] = (
    "Company Research",
    "Portfolio Construction",
    "Sector Reports",
    "Macro Reports",
    "Comparisons",
)

PRIMARY_QUESTION = (
    "Is this investment thesis decision-ready, and what remains unresolved?"
)

MIN_EVIDENCE_COVERAGE = 0.90
MIN_MONITORING_TRIGGERS = 3


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "idre-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IDRE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "final_pre_committee_quality_gate": True,
        "executes_after": "Institutional Debate Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "law": (
            "A strong thesis is not automatically ready for institutional capital allocation. "
            "The Committee receives a structured decision package, never a raw thesis."
        ),
        "dimensions": list(READINESS_DIMENSIONS),
        "weights": dict(READINESS_WEIGHTS),
        "states": list(READINESS_STATES),
        "quality_rules": {
            "min_evidence_coverage": MIN_EVIDENCE_COVERAGE,
            "completed_falsification_cycle": 1,
            "minority_opinion_reviewed": 1,
            "min_active_monitoring_triggers": MIN_MONITORING_TRIGGERS,
            "unresolved_critical_policy_violations": 0,
        },
        "benchmark": {
            "min_scenarios": BENCHMARK_MIN_SCENARIOS,
            "research_types": list(RESEARCH_TYPES),
        },
        "extensions": {
            "decision_heat_map": True,
            "objective_go_no_go_conditions": True,
            "capital_allocation_readiness": True,
        },
    }
