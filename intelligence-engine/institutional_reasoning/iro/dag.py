"""Module 2 + 3 — Research DAG and Task Scheduler.

Builds a directed acyclic graph of research tasks and derives the
execution levels: tasks in the same level run in parallel.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iro.schema import ResearchTask

DAG_VERSION = "research-dag-v1.0.0"


def build_dag(tasks: list[ResearchTask]) -> dict[str, Any]:
    ids = {t.task_id for t in tasks}
    nodes = [
        {
            "task_id": t.task_id,
            "label": t.label,
            "committee": t.committee,
            "depends_on": [d for d in t.depends_on if d in ids],
            "dangling_dependencies": [d for d in t.depends_on if d not in ids],
            "optional": t.optional,
            "deliverable": t.deliverable,
        }
        for t in tasks
    ]
    edges = [
        {"source": d, "target": n["task_id"], "kind": "REQUIRED_BY"}
        for n in nodes
        for d in n["depends_on"]
    ]
    levels, cycle = _topological_levels(nodes)
    return {
        "dag_version": DAG_VERSION,
        "nodes": nodes,
        "edges": edges,
        "levels": levels,
        "acyclic": cycle is None,
        "cycle": cycle,
        "dangling": sorted(
            {d for n in nodes for d in n["dangling_dependencies"]}
        ),
        "counts": {"tasks": len(nodes), "edges": len(edges), "levels": len(levels)},
    }


def _topological_levels(nodes: list[dict[str, Any]]) -> tuple[list[list[str]], list[str] | None]:
    """Kahn layering: each level is a parallel-safe batch."""
    remaining = {n["task_id"]: set(n["depends_on"]) for n in nodes}
    levels: list[list[str]] = []
    done: set[str] = set()

    while remaining:
        ready = sorted([tid for tid, deps in remaining.items() if not (deps - done)])
        if not ready:
            # Cycle — report the unresolved remainder
            return levels, sorted(remaining)
        levels.append(ready)
        done.update(ready)
        for tid in ready:
            remaining.pop(tid, None)
    return levels, None


def execution_plan(dag: dict[str, Any]) -> dict[str, Any]:
    levels = dag.get("levels") or []
    return {
        "levels": levels,
        "parallel_groups": [lvl for lvl in levels if len(lvl) > 1],
        "sequential_depth": len(levels),
        "max_parallelism": max((len(lvl) for lvl in levels), default=0),
        "order": [tid for lvl in levels for tid in lvl],
        "acyclic": dag.get("acyclic", True),
    }
