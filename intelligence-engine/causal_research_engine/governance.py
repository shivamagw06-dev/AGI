"""CRE lifecycle transitions. Models may propose, never approve."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from causal_research_engine.schema import CausalRelationship, KNOWLEDGE_STATUSES
from causal_research_engine.validation import validate_relationship


_TRANSITIONS = {
    "PROPOSED": {"VALIDATED", "QUARANTINED", "REJECTED"},
    "VALIDATED": {"TRUSTED", "QUARANTINED", "REJECTED", "EXPIRED"},
    "TRUSTED": {"EXPIRED", "SUPERSEDED", "QUARANTINED"},
    "QUARANTINED": {"PROPOSED", "REJECTED"},
    "EXPIRED": {"SUPERSEDED"},
    "REJECTED": set(), "SUPERSEDED": set(),
}


def transition_status(row: CausalRelationship, target: str, *, actor_type: str, actor_id: str) -> dict:
    wanted = str(target or "").upper()
    actor = str(actor_type or "").lower()
    if wanted not in KNOWLEDGE_STATUSES:
        return {"ok": False, "status": "INVALID_KNOWLEDGE_STATUS"}
    if actor in {"model", "llm", "ai"} and wanted in {"VALIDATED", "TRUSTED"}:
        return {"ok": False, "status": "MODEL_APPROVAL_FORBIDDEN"}
    if wanted not in _TRANSITIONS.get(row.status, set()):
        return {"ok": False, "status": "INVALID_STATUS_TRANSITION", "from": row.status, "to": wanted}
    candidate = replace(
        row, status=wanted, updated_at=datetime.now(timezone.utc).isoformat(),
        version=f"{row.version}+1", parent_relationship_id=row.relationship_id,
        created_by=actor_id,
    )
    validation = validate_relationship(candidate)
    if wanted in {"VALIDATED", "TRUSTED"} and not validation["ok"]:
        return {"ok": False, "status": "VALIDATION_FAILED", "validation": validation}
    return {"ok": True, "status": wanted, "relationship": candidate}
