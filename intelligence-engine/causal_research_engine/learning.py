"""Document-to-candidate learning. Models may propose, never approve."""
from __future__ import annotations
import hashlib
from typing import Any
from causal_research_engine.event_analysis import normalize_event
from causal_research_engine.schema import CausalRelationship
from causal_research_engine.validation import validate_relationship

def propose_from_document(document: dict[str, Any], *, analysis_as_of: str, candidates: list[CausalRelationship]) -> dict[str, Any]:
    event = normalize_event(document, analysis_as_of=analysis_as_of)
    accepted = []; quarantined = []
    for row in candidates:
        validation = validate_relationship(row, analysis_as_of=analysis_as_of)
        (accepted if validation["ok"] else quarantined).append({"relationship": row, "validation": validation})
    fingerprint = hashlib.sha256(f"{event.event_id}|{tuple(x.relationship_id for x in candidates)}".encode()).hexdigest()
    return {"candidate_batch_id": "CRE-LEARN-" + fingerprint[:16].upper(), "event": event,
            "proposed": accepted, "quarantined": quarantined,
            "promotion_allowed": False, "requires_authorized_review": True}
