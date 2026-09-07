"""Evidence packs from document knowledge — consumed by existing Evidence Factory soft path."""

from __future__ import annotations

from typing import Any

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.schema import EVIDENCE_PACK_KINDS, IDI_VERSION


def generate_packs(
    doc: dict[str, Any],
    obj: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    company = doc.get("company")
    doc_id = doc["document_id"]
    base_meta = {
        "company": company,
        "document_id": doc_id,
        "object_id": obj.get("object_id"),
        "available_from": doc.get("available_from"),
        "replay_id": obj.get("replay_id"),
        "idi_version": IDI_VERSION,
        "fabricated": False,
        "recommendation": None,
    }
    packs: list[dict[str, Any]] = []

    packs.append(
        {
            **base_meta,
            "pack_id": f"idi-document-{doc_id}",
            "kind": "DOCUMENT_PACK",
            "chunk_ids": [c["chunk_id"] for c in chunks],
            "section_labels": obj.get("section_labels") or [],
        }
    )

    def _section_pack(kind: str, labels: set[str]) -> None:
        sel = [c for c in chunks if c.get("section") in labels]
        if not sel:
            return
        packs.append(
            {
                **base_meta,
                "pack_id": f"idi-{kind.lower().replace('_pack','')}-{doc_id}",
                "kind": kind,
                "chunk_ids": [c["chunk_id"] for c in sel],
                "section_labels": sorted(labels),
            }
        )

    _section_pack("MANAGEMENT_PACK", {"MANAGEMENT_DISCUSSION", "STRATEGY", "GUIDANCE"})
    _section_pack("ACCOUNTING_PACK", {"FINANCIAL_STATEMENTS", "NOTES", "TABLES"})
    _section_pack("RISK_PACK", {"RISK_FACTORS"})
    _section_pack("GOVERNANCE_PACK", {"OTHER"} if doc.get("type") in {
        "CORPORATE_GOVERNANCE_REPORT",
        "EXCHANGE_FILING",
        "SHAREHOLDER_NOTICE",
        "VOTING_RESULTS",
        "CORPORATE_POLICY",
    } else set())
    # Always emit governance pack for governance-typed docs using all chunks if no OTHER
    if doc.get("type") in {
        "CORPORATE_GOVERNANCE_REPORT",
        "EXCHANGE_FILING",
        "ESG_REPORT",
        "SHAREHOLDER_NOTICE",
        "POSTAL_BALLOT",
        "VOTING_RESULTS",
        "CORPORATE_POLICY",
        "PROSPECTUS",
        "OFFER_DOCUMENT",
    } and not any(p.get("kind") == "GOVERNANCE_PACK" for p in packs):
        packs.append(
            {
                **base_meta,
                "pack_id": f"idi-governance-{doc_id}",
                "kind": "GOVERNANCE_PACK",
                "chunk_ids": [c["chunk_id"] for c in chunks],
                "section_labels": obj.get("section_labels") or [],
            }
        )
    _section_pack("SEGMENT_PACK", {"BUSINESS_SEGMENTS"})
    if doc.get("type") == "CONFERENCE_CALL_TRANSCRIPT":
        packs.append(
            {
                **base_meta,
                "pack_id": f"idi-transcript-{doc_id}",
                "kind": "TRANSCRIPT_PACK",
                "chunk_ids": [c["chunk_id"] for c in chunks],
                "section_labels": obj.get("section_labels") or [],
            }
        )

    # Ensure kinds are known
    for p in packs:
        assert p["kind"] in EVIDENCE_PACK_KINDS
        store.put_pack(p["pack_id"], p)
    return packs
