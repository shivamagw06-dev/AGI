"""Company-scoped memory helpers."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.registry.index import list_memories


def company_memories(ticker: str) -> list[dict[str, Any]]:
    t = (ticker or "").upper()
    return [
        m
        for m in list_memories()
        if t in {str(e).upper() for e in (m.get("entities") or [])}
    ]
