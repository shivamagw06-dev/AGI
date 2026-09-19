"""CCI-01 quality gates for InstitutionalRelationship objects."""

from __future__ import annotations

from typing import Any

from institutional_cross_company.models import InstitutionalRelationship
from institutional_cross_company.schema import MIN_CONFIDENCE, RELATIONSHIP_TYPES


def validate_relationship(rel: InstitutionalRelationship) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not rel.relationship_id:
        errors.append("missing relationship_id")
    if not rel.source_entity or not rel.target_entity:
        errors.append("unresolved entities")
    if rel.source_entity == rel.target_entity and rel.relationship_type not in {"index_membership"}:
        errors.append("circular relationship without justification")
    if rel.relationship_type not in RELATIONSHIP_TYPES:
        errors.append(f"unknown relationship_type: {rel.relationship_type}")
    if float(rel.confidence) < MIN_CONFIDENCE:
        errors.append("confidence below threshold")
    if not rel.evidence:
        errors.append("no supporting evidence")
    return (len(errors) == 0, errors)


def validate_relationships(
    rels: list[InstitutionalRelationship],
) -> tuple[list[InstitutionalRelationship], dict[str, Any]]:
    ok_rows: list[InstitutionalRelationship] = []
    rejected: list[dict[str, Any]] = []
    seen_pairs: set[str] = set()
    for rel in rels:
        pair = f"{rel.relationship_type}|{rel.source_entity}|{rel.target_entity}"
        rev = f"{rel.relationship_type}|{rel.target_entity}|{rel.source_entity}"
        if pair in seen_pairs or rev in seen_pairs:
            rejected.append({"relationship_id": rel.relationship_id, "errors": ["duplicate relationship"]})
            continue
        ok, errors = validate_relationship(rel)
        if not ok:
            rejected.append({"relationship_id": rel.relationship_id, "errors": errors})
            continue
        seen_pairs.add(pair)
        ok_rows.append(rel)
    return ok_rows, {
        "accepted": len(ok_rows),
        "rejected": len(rejected),
        "rejects": rejected[:20],
        "min_confidence": MIN_CONFIDENCE,
    }
