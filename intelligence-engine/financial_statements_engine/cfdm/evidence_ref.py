"""Evidence Reference object (FSE-03 §12)."""

from __future__ import annotations

from typing import Any


def build_evidence_ref(
    *,
    evidence_id: str,
    source: str,
    source_document: str | None = None,
    page: str | int | None = None,
    section: str | None = None,
    line_reference: str | None = None,
    parser_version: str | None = None,
    collector_version: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    if not evidence_id:
        raise ValueError("evidence_id_required")
    return {
        "evidence_id": evidence_id,
        "source": source,
        "source_document": source_document,
        "page": page,
        "section": section,
        "line_reference": line_reference,
        "parser_version": parser_version,
        "collector_version": collector_version,
        "confidence": confidence,
        "object": "evidence_reference",
    }
