"""Evidence-backed outcome scoring without automatic promotion."""
from __future__ import annotations
import hashlib
from causal_research_engine.schema import CausalRelationship, OutcomeRecord

def record_outcome(relationship: CausalRelationship, *, observed_direction: str, observation_date: str, evidence_ids: tuple[str, ...]) -> OutcomeRecord:
    if observed_direction not in {"POSITIVE", "NEGATIVE", "MIXED", "UNKNOWN"}: raise ValueError("INVALID_OBSERVED_DIRECTION")
    if not evidence_ids: raise ValueError("OUTCOME_EVIDENCE_REQUIRED")
    matched = observed_direction == relationship.direction
    oid = "CRE-OUTCOME-" + hashlib.sha256(f"{relationship.relationship_id}|{observation_date}|{observed_direction}".encode()).hexdigest()[:16].upper()
    return OutcomeRecord(oid, relationship.relationship_id, relationship.direction, observed_direction,
                         observation_date, evidence_ids, matched, .05 if matched else -.08)
