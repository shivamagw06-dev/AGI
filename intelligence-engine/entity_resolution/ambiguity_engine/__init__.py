"""Ambiguity engine — never guess; clarify below threshold / multi-match."""

from __future__ import annotations

from typing import Any

from entity_resolution.confidence import needs_clarification, threshold
from entity_resolution.entity_registry import ambiguous_matches, get_entity


def evaluate_ambiguity(
    *,
    stem: str | None,
    candidates: list[dict[str, Any]],
    best_confidence: float,
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []

    if stem:
        for ent in ambiguous_matches(stem):
            matches.append(_compact(ent, reason=f"ambiguous_stem:{stem}"))

    # Also include unresolved multi-candidate set
    if len(candidates) > 1 and not matches:
        for c in candidates:
            ent = c.get("entity") or {}
            matches.append(_compact(ent, reason="multi_candidate", confidence=c.get("confidence")))

    # Unique high-confidence candidate → clear; multi-match without stem only if close scores
    unique_clear = len(candidates) == 1 and not needs_clarification(best_confidence, 1)
    close_race = False
    if len(candidates) > 1:
        top = float(candidates[0].get("confidence") or 0)
        second = float(candidates[1].get("confidence") or 0)
        close_race = (top - second) < 0.08 or top < threshold()

    clarify = False
    if stem and ambiguous_matches(stem):
        clarify = True
        best_confidence = min(best_confidence, 0.68)
    elif matches and close_race:
        clarify = True
    elif not unique_clear and (close_race or needs_clarification(best_confidence, len(candidates))):
        clarify = True

    return {
        "needs_clarification": clarify,
        "possible_matches": matches,
        "confidence": best_confidence,
        "threshold": threshold(),
        "rule": "If confidence < 85% or stem is ambiguous — stop research and clarify.",
    }


def _compact(ent: dict[str, Any], *, reason: str, confidence: float | None = None) -> dict[str, Any]:
    return {
        "id": ent.get("id"),
        "entity": ent.get("canonical_name"),
        "entity_type": ent.get("entity_type"),
        "ticker": ent.get("ticker"),
        "status": ent.get("status"),
        "reason": reason,
        "confidence": confidence,
    }


def resolve_user_choice(entity_id: str) -> dict[str, Any] | None:
    return get_entity(entity_id)
