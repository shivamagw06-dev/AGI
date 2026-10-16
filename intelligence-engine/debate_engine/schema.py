"""Institutional Debate Engine (IDEB) V1 — RQ2 Sprint 8."""

from __future__ import annotations

from typing import Any

IDEB_VERSION = "1.0.0"
PROGRAMME = "RQ2 — Hypothesis Intelligence"
PROGRAMME_SHORT = "IDEB"
SPRINT = 8
SPRINT_NAME = "Institutional Debate Engine (IDEB) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
MAX_DEBATE_MS_TARGET = 60
BENCHMARK_MIN_SCENARIOS = 2_000
BENCHMARK_MIN_DISAGREEMENTS = 20_000

ANALYSTS: tuple[str, ...] = (
    "Business",
    "Financial",
    "Valuation",
    "Risk",
    "Macro",
    "Portfolio",
    "Management",
)

POSITIONS: tuple[str, ...] = (
    "Strong Support",
    "Support",
    "Neutral",
    "Concern",
    "Strong Concern",
    "Reject",
)

POSITION_SCORES: dict[str, float] = {
    "Strong Support": 1.0,
    "Support": 0.75,
    "Neutral": 0.5,
    "Concern": 0.3,
    "Strong Concern": 0.15,
    "Reject": 0.0,
}

DEBATE_STATES: tuple[str, ...] = (
    "Consensus",
    "Constructive Disagreement",
    "Material Disagreement",
    "Deadlock",
    "Evidence Insufficient",
)

MIN_SUPPORTING_POSITIONS = 3
MIN_CHALLENGED_ASSUMPTIONS = 2
MIN_EVIDENCE_CONFLICTS = 2
MIN_MINORITY_OPINIONS = 1
MIN_UNRESOLVED_QUESTIONS = 1

PRIMARY_QUESTION = (
    "Where does the institutional team disagree, and what evidence would resolve the disagreement?"
)


def constitution_dict() -> dict[str, Any]:
    return {
        "id": "ideb-v1",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IDEB_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "not_another_committee": True,
        "executes_after": "Institutional Thesis Construction Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "law": (
            "Institutional decisions expose disagreement, challenge assumptions and preserve "
            "minority views before the Committee votes."
        ),
        "analysts": list(ANALYSTS),
        "positions": list(POSITIONS),
        "debate_states": list(DEBATE_STATES),
        "quality_rules": {
            "min_supporting_positions": MIN_SUPPORTING_POSITIONS,
            "min_challenged_assumptions": MIN_CHALLENGED_ASSUMPTIONS,
            "min_evidence_conflicts": MIN_EVIDENCE_CONFLICTS,
            "min_minority_opinions": MIN_MINORITY_OPINIONS,
            "min_unresolved_questions": MIN_UNRESOLVED_QUESTIONS,
        },
        "benchmark": {
            "min_debate_scenarios": BENCHMARK_MIN_SCENARIOS,
            "min_analyst_disagreements": BENCHMARK_MIN_DISAGREEMENTS,
        },
        "extensions": {
            "challenge_tournament": True,
            "debate_scorecard": True,
            "position_revision": True,
        },
    }


IDEB_CONSTITUTION: dict[str, Any] = constitution_dict()
