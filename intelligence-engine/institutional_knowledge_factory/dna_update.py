"""Company DNA evolution — append-only updates via IKR."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from institutional_knowledge_runtime.store import load_or_create_company, put
from institutional_knowledge_runtime.versioning import update_assertion


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _claim_index(iko: dict[str, Any]) -> dict[str, int]:
    return {c["claim_id"]: i for i, c in enumerate(iko.get("claims") or []) if c.get("claim_id")}


def update_company_dna(
    entity_id: str,
    claim_updates: list[dict[str, Any]],
    *,
    company: str | None = None,
    reason: str = "Evidence pipeline update",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply append-only claim updates to Company DNA."""
    iko = load_or_create_company(entity_id, company=company)
    changes: list[dict[str, Any]] = []

    for update in claim_updates:
        cid = update.get("claim_id")
        if not cid:
            continue

        idx_map = _claim_index(iko)
        previous = None
        if cid in idx_map:
            previous = dict(iko["claims"][idx_map[cid]])

        try:
            iko = update_assertion(
                iko,
                cid,
                {
                    "status": update.get("state") or update.get("status"),
                    "confidence": update.get("confidence"),
                    "evidence_refs": update.get("evidence_refs"),
                    "monitoring": update.get("monitoring"),
                    "statement": update.get("statement"),
                    "dependencies": update.get("dependencies"),
                    "contradictions": update.get("contradictions"),
                    "evidence_added": [
                        r.get("evidence_id") for r in (update.get("evidence_refs") or [])
                        if isinstance(r, dict) and r.get("evidence_id")
                    ],
                },
                writer="evidence_pipeline",
                reason=reason,
            )
        except KeyError:
            # New claim not in registry — append directly
            new_claim = dict(update)
            new_claim.setdefault("entity_id", entity_id.upper())
            new_claim.setdefault("entity_type", "company")
            new_claim.setdefault("version", 1)
            new_claim.setdefault("owner", "evidence_pipeline")
            new_claim.setdefault("last_review", _now_iso())
            iko.setdefault("claims", []).append(new_claim)

        idx_map = _claim_index(iko)
        current = dict(iko["claims"][idx_map[cid]]) if cid in idx_map else update

        prev_conf = (previous or {}).get("confidence", 0)
        curr_conf = current.get("confidence", 0)
        changes.append({
            "claim_id": cid,
            "previous_assertion": (previous or {}).get("statement"),
            "new_assertion": current.get("statement"),
            "previous_state": (previous or {}).get("state"),
            "new_state": current.get("state"),
            "evidence_added": update.get("evidence_refs") or [],
            "evidence_removed": [],
            "reason": reason,
            "timestamp": _now_iso(),
            "confidence_change": int(curr_conf) - int(prev_conf or 0),
            "impact": _impact_level(previous, current),
        })

    from institutional_knowledge_object.schema import compute_completeness

    iko["completeness"] = compute_completeness(iko.get("claims") or [])
    iko["unknowns"] = [c["claim_id"] for c in iko.get("claims") or [] if str(c.get("state")) == "UNKNOWN"]
    put("company", entity_id, iko)
    return iko, changes


def _impact_level(previous: dict[str, Any] | None, current: dict[str, Any]) -> str:
    if not previous:
        return "new"
    prev_state = str(previous.get("state") or "UNKNOWN")
    curr_state = str(current.get("state") or "UNKNOWN")
    if prev_state == curr_state:
        return "refinement"
    if curr_state in {"CONTRADICTED", "STALE", "UNDER_REVIEW"}:
        return "material_downgrade"
    if curr_state == "SUPPORTED" and prev_state in {"UNKNOWN", "PARTIAL"}:
        return "material_upgrade"
    return "evolution"
