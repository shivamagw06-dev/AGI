"""IMAI memory registry index."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.registry import (
    seeds_commodity,
    seeds_company,
    seeds_macro,
    seeds_policy,
)

_MODULES = (seeds_macro, seeds_commodity, seeds_policy, seeds_company)
_ALL: list[dict[str, Any]] | None = None
_BY_ID: dict[str, dict[str, Any]] | None = None


def _load() -> list[dict[str, Any]]:
    global _ALL, _BY_ID
    if _ALL is not None:
        return _ALL
    rows: list[dict[str, Any]] = []
    for mod in _MODULES:
        rows.extend(list(getattr(mod, "MEMORIES", []) or []))
    rows.sort(key=lambda r: str(r.get("memory_id")))
    _ALL = rows
    _BY_ID = {str(r["memory_id"]): r for r in rows}
    return _ALL


def list_memories(*, memory_type: str | None = None) -> list[dict[str, Any]]:
    rows = _load()
    if memory_type:
        return [r for r in rows if r.get("type") == memory_type]
    return list(rows)


def get_memory(memory_id: str) -> dict[str, Any] | None:
    _load()
    assert _BY_ID is not None
    return _BY_ID.get(memory_id)


def memory_ids() -> list[str]:
    return [str(r["memory_id"]) for r in list_memories()]


def type_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in list_memories():
        t = str(r.get("type") or "unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts


def registry_snapshot() -> dict[str, Any]:
    rows = list_memories()
    return {
        "n": len(rows),
        "type_counts": type_counts(),
        "memory_ids": [r["memory_id"] for r in rows],
        "fabricated": False,
    }
