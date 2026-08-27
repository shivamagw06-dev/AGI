"""Ambiguity detector — consolidate ambiguity signals across validators."""

from __future__ import annotations

from typing import Any


def detect_ambiguity(
    *,
    question_status: dict[str, Any],
    entity_status: dict[str, Any],
    intent_family: str | None = None,
) -> dict[str, Any]:
    flags: list[str] = []
    for issue in question_status.get("issues") or []:
        if issue in {
            "too_many_entities",
            "missing_comparison_target",
            "missing_portfolio_context",
            "multiple_questions",
            "contradictory",
            "incomplete",
            "missing_intent",
        }:
            flags.append(issue)
    for issue in entity_status.get("issues") or []:
        if issue in {"ambiguous_entity", "needs_clarification", "entity_unresolved"}:
            flags.append(issue)

    severity = "none"
    if flags:
        if any(f in flags for f in ("incomplete", "too_many_entities", "ambiguous_entity", "missing_comparison_target", "entity_unresolved")):
            severity = "high"
        else:
            severity = "medium"

    return {
        "ambiguous": bool(flags),
        "flags": sorted(set(flags)),
        "severity": severity,
        "intent_family": intent_family,
        "possible_matches": entity_status.get("possible_matches") or [],
    }
