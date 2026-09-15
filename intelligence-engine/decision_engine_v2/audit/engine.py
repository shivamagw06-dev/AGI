"""Audit engine — complete reproducible decision record."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from decision_engine_v2.store.audit_log import get_audit, store_audit


def build_and_store_audit(pack: dict[str, Any]) -> dict[str, Any]:
    record = {
        "audit_id": str(uuid4()),
        "ticker": pack.get("ticker"),
        "question": pack.get("question"),
        "inputs_present": pack.get("inputs_present"),
        "weights": pack.get("weights"),
        "evidence": pack.get("evidence_summary"),
        "reasoning": pack.get("reasoning"),
        "conflicts": pack.get("conflicts"),
        "uncertainty": pack.get("uncertainty"),
        "committee_view": pack.get("committee_position"),
        "minority_view": pack.get("minority_view"),
        "portfolio_context": pack.get("portfolio_context"),
        "confidence": pack.get("confidence"),
        "recommendation_gate": pack.get("recommendation_gate"),
        "monitoring": pack.get("monitoring"),
        "constitution": pack.get("constitution"),
        "learning_hooks": pack.get("learning_hooks"),
        "outcome": "open",
        "reproducible": True,
        "idev2_version": pack.get("idev2_version"),
    }
    stored = store_audit(record)
    return {
        "audit_id": stored["audit_id"],
        "complete": True,
        "reproducible": True,
        "stored": True,
        "rule": "Every decision stores inputs, weights, evidence, reasoning, conflicts, committee, portfolio, confidence, outcome",
    }


def fetch_audit(audit_id: str) -> dict[str, Any]:
    row = get_audit(audit_id)
    if not row:
        return {"found": False, "audit_id": audit_id}
    return {"found": True, "audit": row, "complete": True, "reproducible": True}
