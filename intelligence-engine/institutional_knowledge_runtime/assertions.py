"""Assertion ↔ IKO claim mapping."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_runtime.schema import IKO_TO_ASSERTION_STATE


def claim_to_assertion(claim: dict[str, Any]) -> dict[str, Any]:
    """Map IKO claim to IKR assertion."""
    state = str(claim.get("state") or "UNKNOWN")
    return {
        "assertion_id": claim.get("claim_id"),
        "entity_id": claim.get("entity_id"),
        "entity_type": claim.get("entity_type", "company"),
        "category": claim.get("category"),
        "claim_type": claim.get("claim_type"),
        "statement": claim.get("statement"),
        "status": IKO_TO_ASSERTION_STATE.get(state, state),
        "confidence": claim.get("confidence", 0),
        "evidence_refs": list(claim.get("evidence_refs") or []),
        "dependencies": list(claim.get("dependencies") or []),
        "contradictions": list(claim.get("contradictions") or []),
        "monitoring": claim.get("monitoring"),
        "version": claim.get("version", 1),
        "timestamp": claim.get("last_review"),
        "author": claim.get("owner", "company_dna"),
        "source": claim.get("template_id"),
        "history": list(claim.get("history") or []),
        "reasoning_summary": claim.get("reasoning_summary"),
    }


def assertion_to_claim(assertion: dict[str, Any]) -> dict[str, Any]:
    """Map IKR assertion back to IKO claim fields."""
    status = str(assertion.get("status") or "UNKNOWN")
    # PARTIAL in IKR may map to ANSWERED or PARTIAL in IKO — preserve if already set
    state = status
    if status == "PARTIAL" and assertion.get("_iko_state") == "ANSWERED":
        state = "ANSWERED"
    return {
        "claim_id": assertion.get("assertion_id"),
        "entity_id": assertion.get("entity_id"),
        "entity_type": assertion.get("entity_type"),
        "category": assertion.get("category"),
        "claim_type": assertion.get("claim_type"),
        "statement": assertion.get("statement"),
        "state": state,
        "confidence": assertion.get("confidence", 0),
        "evidence_refs": list(assertion.get("evidence_refs") or []),
        "dependencies": list(assertion.get("dependencies") or []),
        "contradictions": list(assertion.get("contradictions") or []),
        "monitoring": assertion.get("monitoring"),
        "version": assertion.get("version", 1),
        "last_review": assertion.get("timestamp"),
        "owner": assertion.get("author", "company_dna"),
        "template_id": assertion.get("source"),
        "history": list(assertion.get("history") or []),
        "reasoning_summary": assertion.get("reasoning_summary"),
    }


def assertions_from_iko(iko: dict[str, Any]) -> list[dict[str, Any]]:
    return [claim_to_assertion(c) for c in (iko.get("claims") or []) if isinstance(c, dict)]
