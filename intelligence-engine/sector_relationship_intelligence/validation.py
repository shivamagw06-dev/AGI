"""Relationship validation — no publication without traceable evidence."""

from __future__ import annotations

from typing import Any

from sector_relationship_intelligence.schema import SectorRelationship

VALID_KINDS = {
    "macro_to_sector",
    "sector_to_sector",
    "sector_to_company",
    "company_to_sector",
    "sector_to_market",
    "global_to_sector",
}


def validate_relationship(rel: SectorRelationship) -> list[str]:
    errors: list[str] = []
    if not rel.source or not rel.target:
        errors.append("missing_source_or_target")
    if rel.source == rel.target and not rel.chain:
        errors.append("source_equals_target")
    if not rel.evidence:
        errors.append("evidence_required")
    else:
        for i, ev in enumerate(rel.evidence):
            if not (ev.summary or "").strip():
                errors.append(f"evidence[{i}].summary_required")
            if not ev.kind:
                errors.append(f"evidence[{i}].kind_required")
    if rel.historical_observations < 1:
        errors.append("historical_observations_must_be_positive")
    if rel.confidence_pct < 1 or rel.confidence_pct > 99:
        errors.append("invalid_confidence_pct")
    if rel.kind not in VALID_KINDS:
        errors.append("invalid_kind")
    return errors


def score_confidence(rel: SectorRelationship) -> tuple[int, str, str]:
    n = len(rel.evidence or [])
    weight = sum(float(e.weight) for e in (rel.evidence or []))
    occ = rel.historical_observations
    base = int(rel.confidence_pct or 70)

    if occ >= 8 and n >= 2 and weight >= 2.5:
        label, strength = "High", "High"
        pct = max(base, 88)
    elif occ >= 4 and n >= 2 and weight >= 2.0:
        label, strength = "High", "High"
        pct = max(base, 85)
    elif occ >= 2 and n >= 1:
        label, strength = "Medium", "Medium"
        pct = min(max(base, 70), 87)
    else:
        label, strength = "Low", "Low"
        pct = min(base, 65)

    layers = set(rel.supporting_layers or [])
    if label == "High" and len(layers) < 2 and n < 2:
        label, strength, pct = "Medium", "Medium", min(pct, 82)

    return min(97, pct), label, strength


def is_stale(rel: SectorRelationship, *, as_of_year: int = 2026) -> bool:
    try:
        last = int(str(rel.last_confirmed or "0")[:4])
    except ValueError:
        return True
    return (as_of_year - last) >= 4
