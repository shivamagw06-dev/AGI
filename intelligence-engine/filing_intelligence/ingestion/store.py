"""Append-only filing memory store — nothing is overwritten."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from filing_intelligence.ingestion.corpus import seed_documents
from filing_intelligence.schema import FilingDocument

_DOCS: dict[str, dict[str, Any]] = {}
_SEEDED = False


def reset_for_tests() -> None:
    global _DOCS, _SEEDED
    _DOCS = {}
    _SEEDED = False


def _ensure_seed() -> None:
    global _SEEDED
    if _SEEDED:
        return
    for d in seed_documents():
        _DOCS[d.doc_id] = d.to_dict()
    _SEEDED = True


def ingest_document(doc: FilingDocument | dict[str, Any]) -> dict[str, Any]:
    """Append a filing. Duplicate doc_id is rejected (immutable memory)."""
    _ensure_seed()
    payload = doc.to_dict() if isinstance(doc, FilingDocument) else dict(doc)
    doc_id = payload.get("doc_id")
    if not doc_id:
        raise ValueError("doc_id_required")
    if doc_id in _DOCS:
        return {"accepted": False, "reason": "duplicate_doc_id", "doc_id": doc_id}
    # basic quality gates
    if not payload.get("ticker") or not payload.get("doc_type"):
        return {"accepted": False, "reason": "missing_identity_fields", "doc_id": doc_id}
    _DOCS[doc_id] = payload
    return {"accepted": True, "doc_id": doc_id, "ticker": payload.get("ticker")}


def all_documents() -> list[dict[str, Any]]:
    _ensure_seed()
    return [deepcopy(d) for d in _DOCS.values()]


def documents_for(ticker: str) -> list[dict[str, Any]]:
    t = ticker.upper().replace(".NS", "").replace(".BO", "")
    aliases = {"HDFC": "HDFCBANK", "NESTLE": "NESTLEIND", "ZOMATO": "ETERNAL"}
    t = aliases.get(t, t)
    return [d for d in all_documents() if d.get("ticker") == t]


def get_document(doc_id: str) -> dict[str, Any] | None:
    _ensure_seed()
    d = _DOCS.get(doc_id)
    return deepcopy(d) if d else None
