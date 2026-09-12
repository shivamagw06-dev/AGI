"""Hypothesis memory — soft store of generated theses for learning hooks."""

from __future__ import annotations

from typing import Any

_MEMORY: list[dict[str, Any]] = []


def remember_generation(row: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "question": row.get("question"),
        "hypothesis_ids": [h.get("id") for h in (row.get("hypotheses") or [])],
        "top_hypothesis": (row.get("hypotheses") or [{}])[0].get("statement") if row.get("hypotheses") else None,
        "overall_confidence": row.get("overall_confidence"),
        "timestamp": (row.get("metrics") or {}).get("generated_at"),
        "learning": {"feed_into": "ILM", "stage": "pre_research_hypotheses"},
    }
    _MEMORY.append(entry)
    if len(_MEMORY) > 500:
        del _MEMORY[:-500]
    return entry


def recent(limit: int = 20) -> list[dict[str, Any]]:
    return list(reversed(_MEMORY[-limit:]))


def memory_stats() -> dict[str, Any]:
    return {"stored": len(_MEMORY), "recent": recent(5)}
