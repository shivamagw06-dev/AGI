"""Module 9 — Orchestration Telemetry.

Task → duration → dependencies → evidence → DJG → success / failure.
Planning becomes measurable.
"""

from __future__ import annotations

from typing import Any

TELEMETRY_VERSION = "orchestration-telemetry-v1.0.0"


def task_rows(package: dict[str, Any]) -> list[dict[str, Any]]:
    goal = package.get("goal") or {}
    dag_nodes = {n["task_id"]: n for n in (package.get("dag") or {}).get("nodes") or []}
    rows: list[dict[str, Any]] = []
    for r in package.get("tasks") or []:
        djg = r.get("justification_graph") or {}
        integrity = djg.get("integrity") or {}
        node = dag_nodes.get(r.get("task_id")) or {}
        rows.append(
            {
                "telemetry_version": TELEMETRY_VERSION,
                "assignment_id": package.get("assignment_id"),
                "goal_type": goal.get("goal_type"),
                "entity_id": goal.get("entity_id"),
                "task_id": r.get("task_id"),
                "label": r.get("label"),
                "committee": r.get("committee"),
                "question": r.get("question"),
                "status": r.get("status"),
                "success": r.get("status") in {"executed", "adapted"},
                "duration_ms": r.get("duration_ms"),
                "depends_on": node.get("depends_on") or [],
                "optional": bool(node.get("optional")),
                "missing_evidence": r.get("missing_evidence") or [],
                "adaptations": [a.get("route") for a in (r.get("adaptations") or [])],
                "djg_nodes": (djg.get("counts") or {}).get("nodes"),
                "djg_valid": integrity.get("valid"),
                "djg_gated": integrity.get("gated"),
                "confidence": r.get("confidence"),
            }
        )
    return rows


def orchestration_summary(package: dict[str, Any]) -> dict[str, Any]:
    rows = task_rows(package)
    total = len(rows)
    success = sum(1 for r in rows if r["success"])
    adapted = sum(1 for r in rows if r["adaptations"])
    plan = package.get("execution_plan") or {}
    djg_valid = sum(1 for r in rows if r["djg_valid"])
    return {
        "telemetry_version": TELEMETRY_VERSION,
        "assignment_id": package.get("assignment_id"),
        "tasks": total,
        "succeeded": success,
        "failed": total - success,
        "success_rate_pct": round(100.0 * success / total, 2) if total else 0.0,
        "adapted_tasks": adapted,
        "sequential_depth": plan.get("sequential_depth"),
        "max_parallelism": plan.get("max_parallelism"),
        "parallel_groups": len(plan.get("parallel_groups") or []),
        "total_duration_ms": sum(int(r.get("duration_ms") or 0) for r in rows),
        "wall_clock_ms": package.get("duration_ms"),
        "djg_coverage_pct": round(100.0 * djg_valid / total, 2) if total else 0.0,
    }


def persist(package: dict[str, Any]) -> dict[str, Any]:
    """Append-only sink reuse — never blocks orchestration."""
    rows = task_rows(package)
    try:
        from institutional_reasoning.telemetry_sink import persist_rows

        return persist_rows(rows)
    except Exception as exc:  # sink unavailable in tests / offline
        return {"ok": False, "sink": "unavailable", "written": 0, "error": str(exc)[:200]}
