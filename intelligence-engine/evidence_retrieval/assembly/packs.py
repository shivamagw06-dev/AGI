"""Assemble ranked evidence into typed Evidence Packs — no conclusions."""

from __future__ import annotations

from typing import Any

from evidence_retrieval.schema import PACK_KINDS
from evidence_retrieval.store import put_pack, utc_now


_TYPE_TO_PACK = {
    "FINANCIAL_METRICS": "COMPANY_EVIDENCE_PACK",
    "OWNERSHIP": "COMPANY_EVIDENCE_PACK",
    "CORPORATE_EVENTS": "COMPANY_EVIDENCE_PACK",
    "TIMELINES": "HISTORICAL_EVIDENCE_PACK",
    "HISTORICAL_VALUATION": "HISTORICAL_EVIDENCE_PACK",
    "GOVERNMENT_POLICIES": "GOVERNMENT_EVIDENCE_PACK",
    "MACRO_INDICATORS": "MACRO_EVIDENCE_PACK",
    "ALTERNATIVE_DATA": "CROSS_DOMAIN_EVIDENCE_PACK",
    "RELATIONSHIP_GRAPH": "INDUSTRY_EVIDENCE_PACK",
    "DOCUMENT_SECTIONS": "DOCUMENT_EVIDENCE_PACK",
    "ACCOUNTING_NOTES": "DOCUMENT_EVIDENCE_PACK",
    "RISK_FACTORS": "DOCUMENT_EVIDENCE_PACK",
    "MANAGEMENT_COMMENTARY": "DOCUMENT_EVIDENCE_PACK",
    "CONFERENCE_CALLS": "DOCUMENT_EVIDENCE_PACK",
    "INVESTOR_PRESENTATIONS": "DOCUMENT_EVIDENCE_PACK",
}


def assemble_packs(
    ranked: list[dict[str, Any]],
    *,
    retrieval_id: str,
    discovery: dict[str, Any],
    top_n: int = 40,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in PACK_KINDS}
    for item in ranked[:top_n]:
        kind = _TYPE_TO_PACK.get(str(item.get("evidence_type")), "CROSS_DOMAIN_EVIDENCE_PACK")
        buckets[kind].append(item)
    if discovery.get("portfolio_context"):
        buckets["PORTFOLIO_EVIDENCE_PACK"] = [
            i for i in ranked[:top_n] if i.get("evidence_type") in {"FINANCIAL_METRICS", "OWNERSHIP", "RELATIONSHIP_GRAPH"}
        ]

    packs = []
    companies = discovery.get("companies") or []
    for kind, items in buckets.items():
        if not items:
            continue
        pack_id = f"iere_{kind.lower()}_{retrieval_id}"
        pack = {
            "pack_id": pack_id,
            "kind": kind,
            "retrieval_id": retrieval_id,
            "companies": companies,
            "as_of": discovery.get("as_of"),
            "item_count": len(items),
            "items": [
                {
                    "evidence_id": i.get("evidence_id"),
                    "evidence_type": i.get("evidence_type"),
                    "rank": i.get("rank"),
                    "rank_score": i.get("rank_score"),
                    "title": i.get("title"),
                    "citation": i.get("citation"),
                    "payload": i.get("payload"),
                    "available_from": i.get("available_from"),
                }
                for i in items
            ],
            "citations": [i.get("citation") for i in items if i.get("citation")],
            "avg_confidence": round(
                sum(float(i.get("confidence") or 0) for i in items) / max(len(items), 1), 4
            ),
            "assembled_at": utc_now(),
            "reasoning": False,
            "conclusions": None,
            "recommendation": None,
            "fabricated": False,
        }
        put_pack(pack_id, pack)
        packs.append(pack)
    return packs
