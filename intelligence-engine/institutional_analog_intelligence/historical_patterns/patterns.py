"""Recurring historical pattern tags derived from registry (no fabrication)."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.registry.index import list_memories, type_counts


def pattern_summary() -> dict[str, Any]:
    return {
        "type_counts": type_counts(),
        "n_memories": len(list_memories()),
        "fabricated": False,
        "note": "Patterns are typed seeds only — not LLM-inferred.",
    }
