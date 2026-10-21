"""Compose primary research intent from Sprint 1 ontology (soft dependency)."""

from __future__ import annotations

from typing import Any


def classify_intent(question: str, prior: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return primary/secondary intents without executing layers."""
    if prior and prior.get("primary_intent"):
        return {
            "primary_intent": prior.get("primary_intent"),
            "primary_intent_id": prior.get("primary_intent_id"),
            "secondary_intents": list(prior.get("secondary_intents") or []),
            "source": "prior",
        }
    try:
        from research_ontology.classifier import classify_question

        row = classify_question(question or "")
        return {
            "primary_intent": row.get("primary_intent"),
            "primary_intent_id": row.get("primary_intent_id"),
            "secondary_intents": list(row.get("secondary_intents") or []),
            "entity": row.get("entity"),
            "entity_type": row.get("entity_type"),
            "requires_clarification": bool(row.get("requires_clarification")),
            "possible_matches": row.get("possible_matches"),
            "source": "research_ontology",
        }
    except Exception as exc:  # pragma: no cover - soft fallback
        return {
            "primary_intent": None,
            "secondary_intents": [],
            "source": "fallback",
            "error": str(exc),
        }
