"""Stage 1 — Evidence Classification into institutional domains."""

from __future__ import annotations

from typing import Any

from ask_pipeline.answer_assembly.schema import EVIDENCE_DOMAINS, TYPE_TO_DOMAIN


def classify_evidence(
    *,
    iere_items: list[dict[str, Any]] | None = None,
    evidence_packs: dict[str, Any] | None = None,
    intent_v2: str | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    for raw in iere_items or []:
        if not isinstance(raw, dict):
            continue
        et = str(raw.get("evidence_type") or "")
        domain = TYPE_TO_DOMAIN.get(et, "Other")
        # Soft promote accounting / valuation-framework cues from titles
        title = str(raw.get("title") or "").lower()
        if any(k in title for k in ("p/b", "price-to-book", "residual income", "ev/ebitda", "dcf", "valuation")):
            if domain in {"Financial", "Other", "Historical"}:
                domain = "ValuationFramework"
        if any(k in title for k in ("accounting", "cash flow", "accrual", "notes")):
            if domain in {"Financial", "Other", "Documents"}:
                domain = "Accounting"
        if any(k in title for k in ("moat", "franchise", "business model", "deposit", "utilisation")):
            if domain in {"Financial", "Other", "Industry"}:
                domain = "BusinessModel"
        items.append(
            {
                "evidence_id": raw.get("evidence_id"),
                "domain": domain if domain in EVIDENCE_DOMAINS else "Other",
                "evidence_type": et,
                "title": raw.get("title"),
                "source": raw.get("source"),
                "collector": raw.get("collector"),
                "company": raw.get("company"),
                "document_id": raw.get("document_id"),
                "available_from": raw.get("available_from"),
                "rank_score": raw.get("rank_score"),
                "citation": raw.get("citation"),
                "payload": raw.get("payload"),
                "origin": "iere",
            }
        )

    # Soft-read ask evidence pack envelopes (non-IERE)
    packs = evidence_packs or {}
    for pack_type, pack in packs.items():
        if pack_type == "iere":
            continue
        rows = []
        if isinstance(pack, dict) and "pack_type" in pack:
            rows = [pack]
        elif isinstance(pack, dict):
            rows = [v for v in pack.values() if isinstance(v, dict)]
        for row in rows:
            if not row.get("found"):
                continue
            domain = _pack_domain(str(pack_type))
            items.append(
                {
                    "evidence_id": f"pack_{pack_type}_{row.get('entity') or 'na'}",
                    "domain": domain,
                    "evidence_type": str(pack_type).upper(),
                    "title": f"{pack_type} evidence pack",
                    "source": (row.get("provenance") or {}).get("source") or "ask_pipeline",
                    "collector": (row.get("provenance") or {}).get("collector"),
                    "company": row.get("entity"),
                    "document_id": None,
                    "available_from": ((row.get("point_in_time") or {}).get("as_of")),
                    "rank_score": float(row.get("quality") or 0.5),
                    "citation": row.get("provenance"),
                    "payload": None,  # never dump raw pack into narrative
                    "origin": "ask_pack",
                }
            )

    by_domain: dict[str, list[dict[str, Any]]] = {d: [] for d in EVIDENCE_DOMAINS}
    for item in items:
        by_domain.setdefault(item["domain"], []).append(item)

    return {
        "stage": "evidence_classification",
        "intent_v2": intent_v2,
        "items": items,
        "by_domain": {k: v for k, v in by_domain.items() if v},
        "domain_counts": {k: len(v) for k, v in by_domain.items() if v},
        "item_count": len(items),
        "fabricated": False,
    }


def _pack_domain(pack_type: str) -> str:
    mapping = {
        "company": "Financial",
        "industry": "Industry",
        "government": "Government",
        "relationship": "Relationships",
        "alternative_data": "AlternativeData",
        "expectation": "Financial",
        "portfolio": "Ownership",
        "decision": "Other",
        "macro": "Macro",
    }
    return mapping.get(pack_type, "Other")
