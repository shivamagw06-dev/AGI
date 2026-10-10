"""Decision object compiler — observability snapshot of a past decision."""

from __future__ import annotations

from typing import Any

from decision_quality import store as idq_store
from decision_quality.schema import decision_envelope


def compile_decision_object(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw decision record into the IDQ Decision Object schema."""
    did = str(raw.get("decision_id") or "")
    og = raw.get("outcome_graph") or {}
    evidence = raw.get("evidence_pack") or {}
    obj = decision_envelope(
        did,
        {
            "object_type": "institutional_decision_object",
            "question": raw.get("question"),
            "entity": raw.get("entity"),
            "sector": raw.get("sector"),
            "date": raw.get("date"),
            "available_from": raw.get("available_from") or raw.get("date"),
            "research": raw.get("research") or {},
            "portfolio": raw.get("portfolio") or {},
            "evidence_pack": evidence,
            "frameworks": list(raw.get("frameworks") or []),
            "primary_framework": raw.get("primary_framework"),
            "committee": raw.get("committee") or {},
            "confidence": float(raw.get("confidence") or 0.0),
            "djg": raw.get("djg") or {},
            "pdg": raw.get("pdg") or {},
            "outcome_graph": og,
            "learning_proposal": raw.get("learning_proposal"),
            "macro_regime": raw.get("macro_regime"),
            "prediction_correct": raw.get("prediction_correct"),
            "framework_selection_correct": raw.get("framework_selection_correct"),
            "failure_modes": list(raw.get("failure_modes") or []),
            "outcome_available": bool(og.get("available")),
            "point_in_time": True,
            "fabricated": False,
        },
    )
    idq_store.put_decision(did, obj)
    return obj


def ingest_decisions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [compile_decision_object(r) for r in rows]
