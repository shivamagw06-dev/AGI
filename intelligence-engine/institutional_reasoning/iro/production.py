"""IRO production facade."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iro.memory import snapshot as memory_snapshot
from institutional_reasoning.iro.orchestrator import plan_research, run_assignment
from institutional_reasoning.iro.planning_suite import plan_only_inventory, run_planning_suite
from institutional_reasoning.iro.policies import policy_snapshot
from institutional_reasoning.iro.schema import IRO_VERSION, MODULE_CODE, PROGRAMME
from institutional_reasoning.iro.telemetry import orchestration_summary

__all__ = [
    "dashboard",
    "plan_research",
    "quality_gates",
    "run_assignment",
    "run_planning_suite",
]


def dashboard() -> dict[str, Any]:
    sample = run_assignment("Should I invest £1,000,000 in Infosys?", ticker_hint="INFY")
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IRO_VERSION,
        "policies": policy_snapshot(),
        "plans": plan_only_inventory(),
        "sample_assignment": {
            "objective": sample.get("objective"),
            "goal_type": (sample.get("goal") or {}).get("goal_type"),
            "tasks": len(sample.get("tasks") or []),
            "levels": (sample.get("execution_plan") or {}).get("sequential_depth"),
            "max_parallelism": (sample.get("execution_plan") or {}).get("max_parallelism"),
            "stance": sample.get("stance"),
            "recommendation": sample.get("recommendation"),
            "completeness": sample.get("completeness"),
            "orchestration": orchestration_summary(sample),
        },
        "research_memory": memory_snapshot(),
    }


def quality_gates() -> dict[str, Any]:
    ips = run_planning_suite()
    return {
        "gate": "INSTITUTIONAL_RESEARCH_ORCHESTRATION",
        "version": IRO_VERSION,
        "planning_score": ips.get("score"),
        "avg_djg_coverage_pct": ips.get("avg_djg_coverage_pct"),
        "phase4_gate": ips.get("phase4_gate"),
        "passed": bool((ips.get("phase4_gate") or {}).get("passed")),
        "failures": [r for r in (ips.get("results") or []) if not r.get("passed")],
    }
