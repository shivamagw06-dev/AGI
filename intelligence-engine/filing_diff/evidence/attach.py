"""Evidence attachment for each detected change."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import EVIDENCE_TIERS


def evidence_for_changes(changes: list[dict[str, Any]], documents: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {d.get("doc_id"): d for d in documents}
    rows = []
    for c in changes:
        if c.get("cosmetic") or c.get("materiality") == "ignore":
            continue
        cur = by_id.get(c.get("current_doc_id")) or {}
        prev = by_id.get(c.get("previous_doc_id")) or {}
        tier = int(c.get("evidence_tier") or cur.get("evidence_tier") or 2)
        rows.append(
            {
                "change_id": c.get("change_id"),
                "metric": c.get("metric"),
                "current_document": cur.get("title") or c.get("current_doc_id"),
                "previous_document": prev.get("title") or c.get("previous_doc_id"),
                "current_doc_id": c.get("current_doc_id"),
                "previous_doc_id": c.get("previous_doc_id"),
                "section": c.get("section"),
                "page": c.get("page"),
                "current_date": cur.get("as_of"),
                "previous_date": prev.get("as_of"),
                "evidence_tier": tier,
                "evidence_tier_label": EVIDENCE_TIERS.get(tier, "investor_presentation"),
                "confidence": c.get("confidence"),
            }
        )
    linked = sum(1 for r in rows if r.get("current_doc_id"))
    return {
        "rows": rows,
        "count": len(rows),
        "linked_count": linked,
        "rule": "Every material change must link current and previous filing evidence",
    }
