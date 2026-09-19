"""Relationship validation — no publication without traceable evidence."""

from __future__ import annotations

from typing import Any

from macroeconomic_relationship_intelligence.schema import MacroRelationship


def validate_relationship(rel: MacroRelationship) -> list[str]:
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
    if rel.kind not in {
        "macro_to_company",
        "macro_to_sector",
        "macro_to_market",
        "macro_to_macro",
        "global_to_india",
    }:
        errors.append("invalid_kind")
    return errors


def score_confidence(rel: MacroRelationship) -> tuple[int, str, str]:
    """Evidence-weighted confidence — never invent High without support."""
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

    # Cap High without multi-layer evidence
    layers = set(rel.supporting_layers or [])
    if label == "High" and len(layers) < 2 and n < 2:
        label, strength, pct = "Medium", "Medium", min(pct, 82)

    return min(97, pct), label, strength


def is_stale(rel: MacroRelationship, *, as_of_year: int = 2026) -> bool:
    try:
        last = int(str(rel.last_confirmed or "0")[:4])
    except ValueError:
        return True
    return (as_of_year - last) >= 4
