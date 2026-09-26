"""AGIB Red Team Evaluation Lab."""

from __future__ import annotations

from red_team.capability_gate import gate_check, mark_production_allowed, register_failing_test
from red_team.ecr import attach_ecr_to_package, compute_ecr
from red_team.production import health, package_ecr, quality_gates, run_lab
from red_team.rules import CAPABILITY_GATE_RULE, RED_TEAM_RULES
from red_team.schema import MODULE_CODE, PROGRAMME, VERSION

__all__ = [
    "CAPABILITY_GATE_RULE",
    "MODULE_CODE",
    "PROGRAMME",
    "RED_TEAM_RULES",
    "VERSION",
    "attach_ecr_to_package",
    "compute_ecr",
    "gate_check",
    "health",
    "mark_production_allowed",
    "package_ecr",
    "quality_gates",
    "register_failing_test",
    "run_lab",
]
