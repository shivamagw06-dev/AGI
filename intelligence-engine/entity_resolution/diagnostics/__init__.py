"""ERE diagnostics for admin surfaces."""

from __future__ import annotations

from typing import Any

from entity_resolution.canonical_resolver import resolve_question
from entity_resolution.validation import validate_output


def diagnose(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    row = resolve_question(question, payload)
    return {
        **row,
        "validation": validate_output(row),
        "diagnostics": {
            "mention_count": len(row.get("mentions") or []),
            "has_canonical": bool(row.get("canonical_entity")),
            "kg_linked": bool(row.get("knowledge_graph_linked")),
            "execution_time_ms": row.get("execution_time_ms"),
            "clarification_status": row.get("clarification_status"),
        },
    }
