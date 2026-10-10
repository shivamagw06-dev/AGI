"""S08 — Research / integration DAG executor (dependency + telemetry)."""

from __future__ import annotations

import time
from typing import Any


def execute_research_dag(
    *,
    policy: dict[str, Any],
    planner: dict[str, Any],
    knowledge: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Record integration DAG: knowledge → evidence → attach_planner.

    Institutional reasoning is S09 (single govern_answer). Ask does not call
    IRO run_assignment (would multiply govern_answer). IRO schedule metadata
    is preserved for observability and replay.
    """
    started = time.time()
    if not policy.get("run_dag"):
        return {
            "stage": "research_dag",
            "status": "skipped_by_policy",
            "reason": (policy.get("skips") or {}).get("dag") or "skipped_by_policy",
            "tasks": [],
            "levels": [],
            "duration_ms": int((time.time() - started) * 1000),
        }

    iro_plan = (planner or {}).get("plan") or {}
    iro_levels = ((iro_plan.get("execution_plan") or {}).get("levels")) or []
    tool_plan = (planner or {}).get("tool_plan") or {}
    planned_tools = tool_plan.get("tools") or []

    tasks = [
        {
            "task_id": "knowledge_retrieval",
            "status": knowledge.get("status") or "executed",
            "duration_ms": knowledge.get("duration_ms"),
            "error": knowledge.get("error"),
            "depends_on": [],
        },
        {
            "task_id": "evidence_assembly",
            "status": evidence.get("status") or "executed",
            "duration_ms": evidence.get("duration_ms"),
            "error": evidence.get("error"),
            "depends_on": ["knowledge_retrieval"],
            "coverage": evidence.get("coverage"),
        },
        {
            "task_id": "attach_planner",
            "status": planner.get("status") or "executed",
            "duration_ms": planner.get("duration_ms"),
            "depends_on": ["evidence_assembly"],
            "plan_resolved": planner.get("plan_resolved"),
            "task_count": planner.get("task_count"),
        },
        {
            "task_id": "governed_tool_plan",
            "status": "planned" if planned_tools else "empty",
            "depends_on": ["attach_planner"],
            "registry_version": tool_plan.get("registry_version"),
            "tools": [item.get("name") for item in planned_tools],
            "budgets": tool_plan.get("budgets") or {},
            "controlled_writes_allowed": False,
            "execution_mode": "explicit_bindings_only",
        },
        {
            "task_id": "iro_schedule_observe",
            "status": "executed" if iro_levels else "empty",
            "depends_on": ["governed_tool_plan"],
            "iro_levels": iro_levels,
            "max_parallelism": (iro_plan.get("execution_plan") or {}).get("max_parallelism"),
            "note": "Ask uses plan metadata; task-level govern_answer remains inside S09 once",
        },
    ]
    failures = [t for t in tasks if t.get("status") == "error"]
    withholding = bool(
        (evidence.get("coverage") or 0) <= 0 or evidence.get("packs_found") == 0
    )

    return {
        "stage": "research_dag",
        "status": "executed" if not failures else "degraded",
        "tasks": tasks,
        "levels": [
            ["knowledge_retrieval"],
            ["evidence_assembly"],
            ["attach_planner"],
            ["governed_tool_plan"],
            ["iro_schedule_observe"],
        ],
        "iro_schedule_levels": iro_levels,
        "failures": failures,
        "retry": {"attempted": 0, "policy": "soft_fail_no_retry_default"},
        "failure_propagation": "soft",
        "evidence_withholding": withholding,
        "parallel": {
            "supported": True,
            "mode": "level_parallel_ready",
            "ask_default": "sequential_deterministic",
        },
        "duration_ms": int((time.time() - started) * 1000),
        "fabricated": False,
    }
