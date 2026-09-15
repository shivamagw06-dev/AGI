"""Challenge memory — retain debate patterns for ILM."""

from __future__ import annotations

from typing import Any

_MEMORY: list[dict[str, Any]] = []


def remember_challenges(row: dict[str, Any]) -> dict[str, Any]:
    debate = row.get("debate") or {}
    tournament = debate.get("challenge_tournament") or {}
    entry = {
        "question": row.get("question"),
        "state": (debate.get("consensus") or {}).get("state"),
        "round_count": tournament.get("round_count"),
        "revision_count": tournament.get("revision_count"),
        "minority_count": len(debate.get("minority_report") or []),
        "feed_into": "ILM",
    }
    _MEMORY.append(entry)
    if len(_MEMORY) > 500:
        del _MEMORY[:-500]
    return entry


def memory_stats() -> dict[str, Any]:
    return {"stored": len(_MEMORY), "recent": list(reversed(_MEMORY[-5:]))}
