"""Relationship validation — no publication without traceable evidence."""

from __future__ import annotations

from typing import Any

from app.contracts.models import HistoricalRelationship, RelationshipConfidence


class RelationshipValidationError(ValueError):
    pass


def validate_relationship(rel: HistoricalRelationship) -> list[str]:
    """Return validation errors (empty list = publishable)."""
    errors: list[str] = []
    if not rel.source_key or not rel.target_key:
        errors.append("missing_source_or_target")
    if rel.source_key == rel.target_key and not rel.chain:
        errors.append("source_equals_target")
    if not rel.evidence:
        errors.append("evidence_required")
    else:
        for i, ev in enumerate(rel.evidence):
            if not (ev.summary or "").strip():
                errors.append(f"evidence[{i}].summary_required")
            if not ev.kind:
                errors.append(f"evidence[{i}].kind_required")
    if rel.occurrences < 1:
        errors.append("occurrences_must_be_positive")
    if rel.confidence not in {
        RelationshipConfidence.HIGH,
        RelationshipConfidence.MEDIUM,
        RelationshipConfidence.LOW,
    }:
        errors.append("invalid_confidence")
    return errors


def score_confidence(rel: HistoricalRelationship) -> RelationshipConfidence:
    """Evidence-weighted confidence — never invent High without support."""
    n = len(rel.evidence or [])
    weight = sum(float(e.weight) for e in (rel.evidence or []))
    if rel.occurrences >= 5 and n >= 2 and weight >= 2.0:
        return RelationshipConfidence.HIGH
    if rel.occurrences >= 2 and n >= 1:
        return RelationshipConfidence.MEDIUM
    return RelationshipConfidence.LOW


def to_public(rel: HistoricalRelationship | dict[str, Any]) -> dict[str, Any]:
    if isinstance(rel, HistoricalRelationship):
        data = rel.model_dump(mode="json")
    else:
        data = dict(rel)
    data["providers_queried"] = []
    return data
