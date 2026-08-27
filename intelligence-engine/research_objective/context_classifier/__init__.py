"""Light context signals for ROE (entity type, prior intent, conversation)."""

from __future__ import annotations

from typing import Any


def classify_context(
    question: str,
    *,
    entity_resolution: dict[str, Any] | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ere = entity_resolution or {}
    primary = ere.get("primary_entity") or {}
    entity_type = primary.get("entity_type") or intent.get("entity_type") if intent else None
    entity_name = primary.get("canonical_name") or primary.get("name") or intent.get("entity") if intent else None
    ticker = primary.get("ticker")
    ambiguous = bool(ere.get("requires_clarification") or (intent or {}).get("requires_clarification"))
    return {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "ticker": ticker,
        "entity_id": primary.get("entity_id") or primary.get("id"),
        "entity_ambiguous": ambiguous,
        "question_length": len((question or "").strip()),
        "has_multi_entity_compare": bool(
            ere.get("entities") and isinstance(ere.get("entities"), list) and len(ere.get("entities") or []) >= 2
        ),
    }
