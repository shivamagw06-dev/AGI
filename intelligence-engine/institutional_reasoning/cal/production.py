"""CAL production facade — Learning Governance Layer entry points."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.cal.governance import govern_learning, list_proposals, propose_from_outcome
from institutional_reasoning.cal.learning_suite import run_learning_suite
from institutional_reasoning.cal.overlays import (
    applicability_rules,
    confidence_for,
    contextual_confidence,
    planner_weights,
    policy_overlay,
)
from institutional_reasoning.cal.schema import CAL_VERSION, MODULE_CODE, PHASE7_TARGETS, PROGRAMME
from institutional_reasoning.cal.versions import active_state, list_versions

__all__ = [
    "dashboard",
    "govern_learning",
    "propose_from_outcome",
    "quality_gates",
    "run_learning_suite",
]


def dashboard() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": CAL_VERSION,
        "phase7_targets": PHASE7_TARGETS,
        "active_overlays": active_state(),
        "planner": planner_weights(),
        "policy": policy_overlay(),
        "proposals": len(list_proposals()),
        "versions": len(list_versions()),
        "learning_applied_to_source": False,
        "architecture": {
            "path": [
                "Outcome Intelligence",
                "Learning Proposal",
                "Simulation",
                "Benchmark",
                "Approval",
                "Production Overlay",
            ],
            "forbidden": ["Outcome → Production", "silent self-modification", "rewrite framework"],
        },
    }


def quality_gates() -> dict[str, Any]:
    suite = run_learning_suite()
    return {
        "gate": "CONTINUOUS_ADAPTIVE_LEARNING",
        "version": CAL_VERSION,
        "learning_suite_score": suite.get("score"),
        "traceability_pct": suite.get("traceability_pct"),
        "ungoverned_changes": suite.get("ungoverned_changes"),
        "ies_regressions": suite.get("ies_regressions"),
        "phase7_gate": suite.get("phase7_gate"),
        "passed": bool((suite.get("phase7_gate") or {}).get("passed")),
        "learning_applied_to_source": False,
        "failures": [r for r in (suite.get("results") or []) if not r.get("passed")],
    }


def soft_confidence(framework_id: str, *, regime: str | None = None) -> dict[str, Any]:
    return confidence_for(framework_id, regime=regime)


def soft_contextual_confidence(
    framework_id: str,
    *,
    sector: str | None = None,
    regime: str | None = None,
    horizon: str | None = None,
) -> dict[str, Any]:
    return contextual_confidence(
        framework_id, sector=sector, regime=regime, horizon=horizon
    )


def soft_applicability_rules(**kwargs: Any) -> list[dict[str, Any]]:
    return applicability_rules(**kwargs)
