"""Evidence engine — every fact carries source/document/page/tier."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import EVIDENCE_TIERS


def evidence_pack(facts: list[dict[str, Any]], docs: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {d.get("doc_id"): d for d in docs}
    rows = []
    for f in facts:
        doc = by_id.get(f.get("doc_id")) or {}
        tier = int(f.get("evidence_tier") or doc.get("evidence_tier") or 5)
        rows.append(
            {
                "fact_id": f.get("fact_id"),
                "metric": f.get("metric"),
                "value": f.get("value"),
                "period": f.get("period"),
                "source": doc.get("source_publisher") or "company",
                "document": doc.get("title") or f.get("doc_id"),
                "doc_id": f.get("doc_id"),
                "page": f.get("page"),
                "section": f.get("section"),
                "date": doc.get("as_of"),
                "url": doc.get("url"),
                "confidence": f.get("confidence"),
                "evidence_tier": tier,
                "evidence_tier_label": EVIDENCE_TIERS.get(tier, "external_commentary"),
                "validation_status": f.get("validation_status"),
            }
        )
    tier1 = sum(1 for r in rows if r["evidence_tier"] == 1)
    return {
        "facts": rows,
        "count": len(rows),
        "tier1_count": tier1,
        "rule": "Only official company documents are Tier 1 evidence",
    }
