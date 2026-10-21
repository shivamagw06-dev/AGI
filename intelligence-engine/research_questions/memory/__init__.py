"""IRQ memory — soft store of generated research-question sets."""

from __future__ import annotations

from typing import Any

_MEMORY: list[dict[str, Any]] = []


def remember_generation(row: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "question": row.get("question"),
        "hypothesis_count": row.get("hypothesis_count"),
        "research_question_count": row.get("research_question_count"),
        "coverage_pct": (row.get("coverage") or {}).get("coverage_pct"),
        "timestamp": (row.get("metrics") or {}).get("generated_at"),
        "learning": {"feed_into": "ILM", "stage": "pre_evidence_research_questions"},
    }
    _MEMORY.append(entry)
    if len(_MEMORY) > 500:
        del _MEMORY[:-500]
    return entry


def recent(limit: int = 20) -> list[dict[str, Any]]:
    return list(reversed(_MEMORY[-limit:]))


def memory_stats() -> dict[str, Any]:
    return {"stored": len(_MEMORY), "recent": recent(5)}
