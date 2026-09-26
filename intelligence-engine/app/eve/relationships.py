"""Relationship validation — confidence-scored graph edges."""

from __future__ import annotations

from app.eve.models import EvidenceObject, RelationshipEvidence
from app.eve.store import EveStore


_REL_HINTS = {
    "supplier": "supplier",
    "customer": "customer",
    "subsidiary": "subsidiary",
    "parent": "parent",
    "competitor": "competitor",
    "industry": "industry",
    "sector": "sector",
    "raw_material": "raw_material",
    "commodity": "commodity",
    "country": "country",
    "policy": "policy",
}


def validate_relationships(store: EveStore, evidence: EvidenceObject) -> list[RelationshipEvidence]:
    out: list[RelationshipEvidence] = []
    field = (evidence.fact_key or evidence.raw_field or "").lower()
    rel = None
    for hint, name in _REL_HINTS.items():
        if hint in field or hint in (evidence.value_text or "").lower():
            rel = name
            break
    if rel is None or not evidence.company_id:
        return out
    dst = f"entity:{(evidence.value_text or 'unknown')[:48].lower().replace(' ', '_')}"
    edge = RelationshipEvidence(
        src=evidence.company_id,
        rel=rel,
        dst=dst,
        confidence=min(0.95, max(0.4, float(evidence.confidence) * 0.9)),
        evidence_ids=[evidence.evidence_id],
        verification_status=evidence.verification_status,
    )
    store.add_relationship(edge)
    out.append(edge)
    return out
