"""Module 9 — Outcome Memory.

Persist Research → DJG → PDG → Decision → Outcome → Review → Attribution.
NO learning.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

MEMORY_VERSION = "outcome-memory-v1.0.0"

_MEMORY: list[dict[str, Any]] = []


def reset_memory() -> None:
    _MEMORY.clear()


def remember_outcome(record: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "memory_version": MEMORY_VERSION,
        "stored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "decision_id": record.get("decision_id"),
        "ticker": (record.get("lifecycle") or {}).get("ticker"),
        "research_run_id": (record.get("lifecycle") or {}).get("research_run_id"),
        "djg": (record.get("lifecycle") or {}).get("research_djg"),
        "pdg": (record.get("lifecycle") or {}).get("portfolio_djg"),
        "decision": (record.get("lifecycle") or {}).get("decision"),
        "outcome": {
            "total_return": (record.get("market") or {}).get("total_return"),
            "alpha": (record.get("market") or {}).get("alpha"),
        },
        "evaluation": {
            "score": (record.get("evaluation") or {}).get("score"),
            "grade": (record.get("evaluation") or {}).get("grade"),
            "return_error": (record.get("evaluation") or {}).get("return_error"),
        },
        "review": (record.get("review") or {}).get("overall_quality"),
        "attribution": {
            "wrong": (record.get("attribution") or {}).get("wrong"),
            "primary_failure": (record.get("attribution") or {}).get("primary_failure"),
            "unattributed": (record.get("attribution") or {}).get("unattributed"),
        },
        "outcome_graph_ref": (record.get("outcome_graph") or {}).get("decision_id"),
        "learning_applied": False,
    }
    _MEMORY.append(entry)
    if len(_MEMORY) > 300:
        del _MEMORY[:-300]
    return deepcopy(entry)


def recall(ticker: str | None = None) -> list[dict[str, Any]]:
    if not ticker:
        return deepcopy(_MEMORY)
    t = str(ticker).upper()
    return deepcopy([m for m in _MEMORY if str(m.get("ticker") or "").upper() == t])


def snapshot() -> dict[str, Any]:
    return {
        "memory_version": MEMORY_VERSION,
        "count": len(_MEMORY),
        "latest": deepcopy(_MEMORY[-1]) if _MEMORY else None,
        "learning_applied": False,
    }
