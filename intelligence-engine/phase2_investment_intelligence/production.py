"""Phase 2 programme façade — registry only; no engine mutations."""

from __future__ import annotations

from typing import Any

from phase2_investment_intelligence.contract import ENGINE_CONTRACTS, build_engine_contract
from phase2_investment_intelligence.schema import (
    ARCHITECTURE_TARGET,
    BASELINE_NAME,
    BASELINE_STATUS,
    DOC_PATH,
    FROZEN_BASELINE_LOCKS,
    PRIMARY_OBJECTIVE,
    PROGRAMME,
    PROGRAMME_VERSION,
    SUCCESS_CRITERIA,
)
from phase2_investment_intelligence.milestones import (
    IMPLEMENTATION_PR_CHECKLIST,
    milestones_board,
)
from phase2_investment_intelligence.scorecard import DEFINITION_OF_DONE, programme_scorecard_board
from phase2_investment_intelligence.workstreams import workstream_board


def health() -> dict[str, Any]:
    board = workstream_board()
    milestones = milestones_board()
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": PROGRAMME_VERSION,
        "baseline": {"name": BASELINE_NAME, "status": BASELINE_STATUS},
        "architecture_target": ARCHITECTURE_TARGET,
        "primary_objective": PRIMARY_OBJECTIVE,
        "frozen_baseline_locks": dict(FROZEN_BASELINE_LOCKS),
        "success_criteria": list(SUCCESS_CRITERIA),
        "standard_engine_contract": True,
        "intelligence_scorecard": True,
        "definition_of_done": list(DEFINITION_OF_DONE),
        "implementation_pr_checklist": list(IMPLEMENTATION_PR_CHECKLIST),
        "milestones": milestones,
        "workstreams": board,
        "doc": DOC_PATH,
        "extends_intelligence": True,
        "replaces_baseline": False,
        "architecture_complete": True,
        "recommended_first_build": board.get("recommended_first_build"),
        "active_milestone": milestones.get("active"),
        "note": (
            "Phase 2 is an investment intelligence programme. "
            "Architectural design is complete — implement engines under milestones "
            "Phase 2.1 → 2.2 → 2.3. Do not modify Constitution, Governance Spec, "
            "Decision Engine contracts, Institutional Gate, Evaluation Lab, Drift, or IAT."
        ),
    }


def contracts() -> dict[str, Any]:
    """Standard contract declarations for all Phase 2 engines."""
    return {
        "standard_contract": True,
        "engines": {code: build_engine_contract(code) for code in ENGINE_CONTRACTS},
        "failure_mode_rule": "degrade_gracefully_do_not_block_unrelated_engines",
        "consumers": ["decision_engine", "evaluation_lab"],
    }


def scorecard() -> dict[str, Any]:
    """Intelligence Scorecard templates (Phase 2 measurement frame)."""
    return programme_scorecard_board()


def programme() -> dict[str, Any]:
    """Full programme pack for Mission Control / docs consumers."""
    h = health()
    return {
        **h,
        "pipeline": [
            "Investment Committee",
            "Existing Intelligence Engines",
            "NEW Phase 2 Engines",
            "Decision Engine",
            "Institutional Gate",
            "Governance Spec",
            "Evaluation Lab",
            "Drift Engine",
            "Institutional Acceptance Test",
        ],
        "contracts": contracts(),
        "intelligence_scorecard_board": scorecard(),
        "milestones_board": milestones_board(),
        "prohibited": [
            "redesign_constitution",
            "redesign_governance",
            "redesign_evaluation_lab",
            "redesign_decision_engine",
            "redesign_recommendation_readiness",
            "redesign_institutional_readiness",
            "redesign_phase1_architecture",
        ],
    }
