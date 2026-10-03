"""Module 7 — Research Memory.

Stores research goals, plans, execution graphs and outcomes so a
successful plan can be reused for a similar assignment.

This is workflow reuse — not outcome learning (that is a later phase).
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any

MEMORY_VERSION = "research-memory-v1.0.0"

_LOCK = threading.Lock()
_STORE: dict[str, dict[str, Any]] = {}


def plan_key(goal_type: str, entity_id: str | None) -> str:
    raw = f"{str(goal_type or '').lower()}::{str(entity_id or 'ANY').upper()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def remember(
    *,
    goal: dict[str, Any],
    plan: dict[str, Any],
    dag: dict[str, Any],
    outcome: dict[str, Any],
) -> dict[str, Any]:
    key = plan_key(goal.get("goal_type"), goal.get("entity_id"))
    entry = {
        "plan_key": key,
        "goal": goal,
        "task_ids": [n["task_id"] for n in (dag.get("nodes") or [])],
        "levels": dag.get("levels") or [],
        "stance": outcome.get("stance"),
        "can_recommend": outcome.get("can_recommend"),
        "reuse_count": 0,
        "memory_version": MEMORY_VERSION,
    }
    with _LOCK:
        existing = _STORE.get(key)
        if existing:
            entry["reuse_count"] = int(existing.get("reuse_count") or 0)
        _STORE[key] = entry
    return entry


def recall(goal_type: str, entity_id: str | None) -> dict[str, Any] | None:
    key = plan_key(goal_type, entity_id)
    with _LOCK:
        entry = _STORE.get(key)
        if entry:
            entry["reuse_count"] = int(entry.get("reuse_count") or 0) + 1
            _STORE[key] = entry
            return dict(entry)
    return None


def snapshot() -> dict[str, Any]:
    with _LOCK:
        return {
            "memory_version": MEMORY_VERSION,
            "n_plans": len(_STORE),
            "plans": [dict(v) for v in _STORE.values()],
        }


def reset_memory() -> None:
    with _LOCK:
        _STORE.clear()
