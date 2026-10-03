"""Fact versioning — never overwrite; append previous/new/reason/source."""

from __future__ import annotations

from app.eve.models import EvidenceObject, FactVersion
from app.eve.normalise import values_equivalent
from app.eve.store import EveStore


def maybe_version(store: EveStore, evidence: EvidenceObject) -> FactVersion | None:
    prior = [
        e
        for e in store.active_evidence(company_id=evidence.company_id, fact_key=evidence.fact_key)
        if e.evidence_id != evidence.evidence_id
    ]
    if not prior:
        return None
    # Latest prior by created_at
    prior.sort(key=lambda e: e.created_at or "", reverse=True)
    old = prior[0]
    if values_equivalent(old.value_text, evidence.value_text):
        return None
    version = FactVersion(
        fact_key=evidence.fact_key,
        company_id=evidence.company_id,
        previous_value=old.value_text[:800],
        new_value=evidence.value_text[:800],
        reason="new_source_observation",
        effective_date=evidence.provenance.observation_timestamp or evidence.created_at,
        source_id=evidence.provenance.source_id,
        evidence_id=evidence.evidence_id,
        confidence=evidence.confidence,
    )
    store.add_version(version)
    store.audit_event(
        "fact_versioned",
        object_kind="fact_version",
        object_id=version.version_id,
        detail=f"{evidence.fact_key}:{old.value_text[:40]}->{evidence.value_text[:40]}",
    )
    return version


def fact_history(store: EveStore, *, company_id: str | None, fact_key: str) -> list[FactVersion]:
    return [
        v
        for v in store.versions
        if v.fact_key == fact_key and (company_id is None or v.company_id == company_id)
    ]
