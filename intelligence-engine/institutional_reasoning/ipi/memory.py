"""Module 9 — Portfolio Memory.

Stores snapshots of decisions — no learning.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

MEMORY_VERSION = "portfolio-memory-v1.0.0"

_MEMORY: list[dict[str, Any]] = []


def reset_memory() -> None:
    _MEMORY.clear()


def remember(decision: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "memory_version": MEMORY_VERSION,
        "stored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "portfolio_snapshot": deepcopy(decision.get("portfolio_snapshot") or {}),
        "decision": {
            "action": (decision.get("committee") or {}).get("action"),
            "target_weight": (decision.get("sizing") or {}).get("target_weight"),
            "entity_id": decision.get("entity_id"),
            "withheld": bool(decision.get("withheld")),
        },
        "research_package_ref": decision.get("research_run_id"),
        "djg_reference": decision.get("djg_reference"),
        "pdg_reference": (decision.get("portfolio_decision_graph") or {}).get("run_id"),
        "constraints": decision.get("policy") or {},
        "position_size": decision.get("sizing") or {},
        "scenarios": (decision.get("scenarios") or {}).get("scenarios") or {},
    }
    _MEMORY.append(entry)
    # Cap memory to keep tests deterministic / light
    if len(_MEMORY) > 200:
        del _MEMORY[:-200]
    return entry


def recall(entity_id: str | None = None) -> list[dict[str, Any]]:
    if not entity_id:
        return list(_MEMORY)
    eid = str(entity_id).upper()
    return [m for m in _MEMORY if str((m.get("decision") or {}).get("entity_id") or "").upper() == eid]


def snapshot() -> dict[str, Any]:
    return {
        "memory_version": MEMORY_VERSION,
        "count": len(_MEMORY),
        "latest": _MEMORY[-1] if _MEMORY else None,
    }
