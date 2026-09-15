"""Conflict detection — preserve both sides; never silent overwrite."""

from __future__ import annotations

from app.eve.models import ConflictRecord, EvidenceObject, VerificationTask
from app.eve.normalise import values_equivalent
from app.eve.store import EveStore


def detect_conflicts(store: EveStore, evidence: EvidenceObject) -> list[ConflictRecord]:
    if not store or evidence.soft_deleted:
        return []
    peers = [
        e
        for e in store.active_evidence(company_id=evidence.company_id, fact_key=evidence.fact_key)
        if e.evidence_id != evidence.evidence_id
    ]
    found: list[ConflictRecord] = []
    for peer in peers:
        if values_equivalent(evidence.value_text, peer.value_text):
            continue
        # Same fact key, materially different values → conflict
        conflict = ConflictRecord(
            company_id=evidence.company_id,
            fact_key=evidence.fact_key,
            left_evidence_id=peer.evidence_id,
            right_evidence_id=evidence.evidence_id,
            left_value=peer.value_text[:500],
            right_value=evidence.value_text[:500],
            left_source_id=peer.provenance.source_id,
            right_source_id=evidence.provenance.source_id,
            status="open",
            severity=_severity(evidence, peer),
            verification_task=f"Reconcile {evidence.fact_key} for {evidence.company_symbol or evidence.company_id or 'macro'}",
        )
        # Dedup similar open conflicts
        dup = False
        for existing in store.conflicts.values():
            if existing.status != "open":
                continue
            if existing.fact_key == conflict.fact_key and existing.company_id == conflict.company_id:
                ids = {existing.left_evidence_id, existing.right_evidence_id}
                if conflict.left_evidence_id in ids and conflict.right_evidence_id in ids:
                    dup = True
                    break
        if dup:
            continue
        store.add_conflict(conflict)
        store.add_task(
            VerificationTask(
                kind="conflict_resolution",
                company_id=evidence.company_id,
                fact_key=evidence.fact_key,
                title=conflict.verification_task,
                detail=f"{conflict.left_value[:120]} vs {conflict.right_value[:120]}",
                priority=conflict.severity,
            )
        )
        # Mark both as conflicted (new copies — immutable style via replace in store)
        store.evidence[peer.evidence_id] = peer.model_copy(update={"verification_status": "conflicted"})
        store.evidence[evidence.evidence_id] = evidence.model_copy(update={"verification_status": "conflicted"})
        store.audit_event(
            "conflict_detected",
            object_kind="conflict",
            object_id=conflict.conflict_id,
            detail=conflict.fact_key,
        )
        found.append(conflict)
    return found


def _severity(a: EvidenceObject, b: EvidenceObject) -> str:
    key = (a.fact_key or "").lower()
    if key in {"revenue", "pat", "debt", "guidance"}:
        return "high"
    if abs(float(a.confidence) - float(b.confidence)) > 0.25:
        return "medium"
    return "medium"
