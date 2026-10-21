"""Page/section/paragraph provenance helpers."""

from __future__ import annotations

from typing import Any


def fact_provenance(
    *,
    document_id: str,
    page: int | None,
    section: str | None,
    paragraph: int | None,
    collector: str | None,
    validator: str | None,
    timestamp: str,
    checksum: str | None,
) -> dict[str, Any]:
    return {
        "source_document": document_id,
        "page": page,
        "section": section,
        "paragraph": paragraph,
        "collector": collector,
        "validator": validator,
        "timestamp": timestamp,
        "checksum": checksum,
    }


def assert_chunk_provenance(chunk: dict[str, Any]) -> bool:
    prov = chunk.get("provenance") or {}
    required = ("source_document", "page", "section", "collector", "timestamp", "checksum")
    return all(prov.get(k) is not None and prov.get(k) != "" for k in required)
