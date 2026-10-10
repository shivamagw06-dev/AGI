"""Compile typed document knowledge objects — no reasoning."""

from __future__ import annotations

from typing import Any

from knowledge_factory.institutional_documents.schema import DOC_TYPE_TO_OBJECT, IDI_VERSION


def compile_document_object(
    doc: dict[str, Any],
    parsed: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    doc_type = str(doc.get("type") or "EXCHANGE_FILING")
    object_type = DOC_TYPE_TO_OBJECT.get(doc_type, "GovernanceObject")
    obj_id = f"{object_type}_{doc['document_id']}"
    section_index = [
        {
            "section": s.get("section"),
            "heading": s.get("heading"),
            "page": s.get("page"),
            "paragraph": s.get("paragraph"),
            "char_count": s.get("char_count"),
        }
        for s in (parsed.get("sections") or [])
    ]
    return {
        "object_id": obj_id,
        "object_type": object_type,
        "document_id": doc["document_id"],
        "company": doc.get("company"),
        "type": doc_type,
        "title": doc.get("title"),
        "version": doc.get("version"),
        "published_date": doc.get("published_date"),
        "available_from": doc.get("available_from"),
        "retrieved_at": doc.get("retrieved_at"),
        "language": doc.get("language"),
        "checksum": doc.get("checksum"),
        "pages": doc.get("pages") or parsed.get("pages"),
        "sections": section_index,
        "section_labels": parsed.get("extracted_labels") or [],
        "chunk_count": len(chunks),
        "chunk_ids": [c["chunk_id"] for c in chunks],
        "source": doc.get("source"),
        "collector": doc.get("collector"),
        "validator": (doc.get("validation") or {}).get("validator"),
        "confidence": 0.9 if doc.get("mode") in {"injected", "recorded_sample"} else 0.75,
        "replay_id": f"replay_{doc['document_id']}",
        "point_in_time": True,
        "provenance": doc.get("provenance"),
        "idi_version": IDI_VERSION,
        "reasoning": False,
        "summarisation": False,
        "recommendation": None,
        "fabricated": False,
    }
