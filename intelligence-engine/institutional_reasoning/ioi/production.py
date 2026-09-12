"""IOI production facade — soft-wire under institutional_reasoning."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ioi.lifecycle import list_decisions, store_snapshot
from institutional_reasoning.ioi.memory import snapshot as memory_snapshot
from institutional_reasoning.ioi.outcome_suite import run_outcome_suite
from institutional_reasoning.ioi.pipeline import evaluate_decision, track_decision
from institutional_reasoning.ioi.schema import IOI_VERSION, MODULE_CODE, PHASE6_TARGETS, PROGRAMME
from institutional_reasoning.ioi.scoreboard import build_scoreboard

__all__ = [
    "dashboard",
    "evaluate_decision",
    "quality_gates",
    "run_outcome_suite",
    "track_decision",
]


def dashboard() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IOI_VERSION,
        "phase6_targets": PHASE6_TARGETS,
        "lifecycle": store_snapshot(),
        "outcome_memory": memory_snapshot(),
        "scoreboard": build_scoreboard(),
        "open_decisions": len(list_decisions(status="open")),
        "learning_applied": False,
        "note": "Measures outcomes only — Phase 7 may learn from this memory.",
    }


def quality_gates() -> dict[str, Any]:
    suite = run_outcome_suite()
    return {
        "gate": "INSTITUTIONAL_OUTCOME_INTELLIGENCE",
        "version": IOI_VERSION,
        "outcome_suite_score": suite.get("score"),
        "traceability_pct": suite.get("traceability_pct"),
        "unattributed_failures": suite.get("unattributed_failures"),
        "phase6_gate": suite.get("phase6_gate"),
        "passed": bool((suite.get("phase6_gate") or {}).get("passed")),
        "learning_applied": False,
        "failures": [r for r in (suite.get("results") or []) if not r.get("passed")],
    }
