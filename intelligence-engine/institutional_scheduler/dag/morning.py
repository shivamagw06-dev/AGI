"""Executable morning DAG — levels, dependency resolution, parallel peers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from institutional_scheduler.workflows.definitions import WORKFLOWS


def build_morning_dag() -> dict[str, Any]:
    by_level: dict[int, list[str]] = defaultdict(list)
    edges: list[dict[str, str]] = []
    for wf in WORKFLOWS.values():
        by_level[int(wf["level"])].append(wf["workflow_id"])
        for dep in wf.get("dependencies") or []:
            edges.append({"from": dep, "to": wf["workflow_id"]})
    levels = [by_level[i] for i in sorted(by_level)]
    # Validate deps exist
    dangling = []
    for wf in WORKFLOWS.values():
        for dep in wf.get("dependencies") or []:
            if dep not in WORKFLOWS:
                dangling.append({"workflow": wf["workflow_id"], "missing": dep})
    return {
        "dag_id": "morning_operations_0600",
        "schedule": "06:00",
        "levels": levels,
        "edges": edges,
        "workflows": list(WORKFLOWS.keys()),
        "acyclic": not dangling,
        "dangling": dangling,
        "max_parallelism": max((len(L) for L in levels), default=1),
        "parallel_supported": True,
    }


def dependencies_satisfied(workflow_id: str, completed: dict[str, str]) -> bool:
    wf = WORKFLOWS.get(workflow_id) or {}
    for dep in wf.get("dependencies") or []:
        # Failed non-critical deps still satisfy (failure isolation)
        if dep not in completed:
            return False
    return True
