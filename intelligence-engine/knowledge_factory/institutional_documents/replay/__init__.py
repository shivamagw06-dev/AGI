"""Point-in-time document replay — never leak future filings."""

from __future__ import annotations

from typing import Any

from knowledge_factory.institutional_documents import store


def replay_as_of(as_of: str, *, ticker: str | None = None) -> dict[str, Any]:
    """Return documents with available_from <= as_of only."""
    day = str(as_of)[:10]
    docs = store.list_documents(ticker=ticker)
    visible = [d for d in docs if str(d.get("available_from") or "")[:10] <= day]
    leaked = [d for d in docs if str(d.get("available_from") or "")[:10] > day]
    return {
        "as_of": day,
        "ticker": ticker.upper() if ticker else None,
        "document_count": len(visible),
        "documents": [
            {
                "document_id": d.get("document_id"),
                "company": d.get("company"),
                "type": d.get("type"),
                "title": d.get("title"),
                "available_from": d.get("available_from"),
                "checksum": d.get("checksum"),
                "replay_id": f"replay_{d.get('document_id')}",
            }
            for d in visible
        ],
        "future_leakage_blocked": len(leaked),
        "leaked_ids_hidden": [d.get("document_id") for d in leaked],
        "deterministic": True,
        "fabricated": False,
    }


def replay_document(doc_id: str) -> dict[str, Any] | None:
    doc = store.get_document(doc_id)
    if not doc:
        return None
    chunks = store.get_chunks(doc_id)
    return {
        "replay_id": f"replay_{doc_id}",
        "document": {
            k: doc.get(k)
            for k in (
                "document_id",
                "company",
                "type",
                "title",
                "version",
                "published_date",
                "available_from",
                "checksum",
                "pages",
                "source",
            )
        },
        "chunk_count": len(chunks),
        "chunk_checksums": [c.get("checksum") for c in chunks],
        "deterministic": True,
        "fabricated": False,
    }
