"""Contradiction detection and linking."""

from __future__ import annotations

from typing import Any


def resolve_contradictions(
    assertions: list[dict[str, Any]],
    evidence_packs: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Mark assertions CONTRADICTED when evidence or linked assertions conflict."""
    evidence_packs = evidence_packs or {}
    by_id: dict[str, dict[str, Any]] = {
        str(a.get("assertion_id")): dict(a) for a in assertions if a.get("assertion_id")
    }

    for aid, assertion in list(by_id.items()):
        pack = evidence_packs.get(aid) or {}
        contradicting = pack.get("contradicting") or []
        linked = assertion.get("contradictions") or []
        has_conflict = bool(contradicting) or bool(linked)

        if has_conflict and str(assertion.get("status")) not in {"DEPRECATED", "UNKNOWN"}:
            updated = dict(assertion)
            updated["status"] = "CONTRADICTED"
            if contradicting:
                updated["_contradicting_evidence"] = [e.get("evidence_id") for e in contradicting]
            by_id[aid] = updated

    return list(by_id.values())


def list_contradictions(assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return assertions in CONTRADICTED state with linked refs."""
    out: list[dict[str, Any]] = []
    for a in assertions:
        if str(a.get("status")) == "CONTRADICTED":
            out.append({
                "assertion_id": a.get("assertion_id"),
                "statement": a.get("statement"),
                "contradictions": a.get("contradictions") or [],
                "contradicting_evidence": a.get("_contradicting_evidence") or [],
            })
    return out
