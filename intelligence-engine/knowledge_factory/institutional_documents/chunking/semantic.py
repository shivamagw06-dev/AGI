"""Semantic chunking with page/section provenance and replay fields."""

from __future__ import annotations

from typing import Any

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.embeddings import embed_text


def chunk_parsed(
    doc: dict[str, Any],
    parsed: dict[str, Any],
    *,
    max_chars: int = 1200,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    doc_id = str(doc["document_id"])
    for i, sec in enumerate(parsed.get("sections") or []):
        text = str(sec.get("text") or "")
        parts = _split(text, max_chars)
        for j, part in enumerate(parts):
            chunk_id = f"{doc_id}_c{i:03d}_{j:02d}"
            emb = embed_text(part)
            chunk = {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "company": doc.get("company"),
                "document_type": doc.get("type"),
                "section": sec.get("section"),
                "page": sec.get("page"),
                "paragraph": sec.get("paragraph"),
                "heading": sec.get("heading"),
                "text": part,
                "embedding": emb,
                "checksum": store.checksum_text(part),
                "available_from": doc.get("available_from"),
                "retrieved_at": doc.get("retrieved_at"),
                "replay_id": f"replay_{doc_id}",
                "provenance": {
                    "source_document": doc_id,
                    "page": sec.get("page"),
                    "section": sec.get("section"),
                    "paragraph": sec.get("paragraph"),
                    "collector": doc.get("collector"),
                    "validator": (doc.get("validation") or {}).get("validator"),
                    "timestamp": store.utc_now(),
                    "checksum": store.checksum_text(part),
                },
                "fabricated": False,
            }
            chunks.append(chunk)
    return chunks


def _split(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    parts = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            # break on paragraph/sentence boundary when possible
            cut = text.rfind("\n\n", start, end)
            if cut <= start:
                cut = text.rfind(". ", start, end)
            if cut > start:
                end = cut + 1
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]
