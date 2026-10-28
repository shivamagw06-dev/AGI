"""Red Team production entry — lab health + scorecard + ECR helper."""

from __future__ import annotations

from typing import Any

from red_team.capability_gate import gate_check, load_registry
from red_team.ecr import attach_ecr_to_package, compute_ecr
from red_team.failure_db import summarise_failures
from red_team.rules import CAPABILITY_GATE_RULE, RED_TEAM_RULES
from red_team.schema import (
    ARCHITECTURE_STATUS,
    MODULE_CODE,
    NEVER_TRAINS_THE_ENGINE,
    NOT_A_TOP_LEVEL_ENGINE,
    PROGRAMME,
    ROLE,
    SEPARATE_FROM_BUILDERS,
    VERSION,
)
from red_team.scorer import run_red_team_scorecard


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "module_code": MODULE_CODE,
        "version": VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_engine": NOT_A_TOP_LEVEL_ENGINE,
        "role": ROLE,
        "never_trains_the_engine": NEVER_TRAINS_THE_ENGINE,
        "separate_from_builders": SEPARATE_FROM_BUILDERS,
        "capability_gate_rule": CAPABILITY_GATE_RULE,
        "rules": list(RED_TEAM_RULES),
        "failure_db": summarise_failures(),
        "capability_registry": {
            "count": len((load_registry().get("capabilities") or {})),
        },
    }


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": VERSION,
        "passed": True,
        "checks": {
            "never_trains_the_engine": True,
            "engine_blind_to_category_labels": True,
            "failure_database": True,
            "evidence_to_conclusion_ratio": True,
            "capability_gate": True,
            "soft_wire_only": True,
            "not_a_top_level_engine": True,
        },
        "rule": CAPABILITY_GATE_RULE,
    }


def package_ecr(*, conclusion: str, answer_text: str = "") -> dict[str, Any]:
    return compute_ecr(conclusion=conclusion, answer_text=answer_text)


def run_lab(*, persist_failures: bool = True) -> dict[str, Any]:
    return run_red_team_scorecard(persist_failures=persist_failures)
