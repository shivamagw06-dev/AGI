"""Citation builder — never lose provenance."""

from __future__ import annotations

from typing import Any

from evidence_retrieval.store import utc_now


def build_citation(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": item.get("evidence_id"),
        "knowledge_object": item.get("knowledge_object"),
        "source": item.get("source"),
        "collector": item.get("collector") or item.get("source"),
        "document": item.get("document_id"),
        "document_id": item.get("document_id"),
        "section": item.get("section"),
        "page": item.get("page"),
        "paragraph": item.get("paragraph"),
        "timestamp": item.get("retrieved_at") or utc_now(),
        "available_from": item.get("available_from"),
        "checksum": item.get("checksum"),
        "version": item.get("version") or "1",
        "confidence": item.get("confidence"),
        "fabricated": False,
    }


def attach_citations(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in ranked:
        row = dict(item)
        row["citation"] = build_citation(row)
        out.append(row)
    return out


def citation_coverage(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(ranked)
    complete = 0
    for item in ranked:
        cit = item.get("citation") or {}
        if cit.get("source") and cit.get("knowledge_object") and cit.get("evidence_id"):
            complete += 1
    return {
        "total": n,
        "complete": complete,
        "coverage": round(complete / n, 4) if n else 0.0,
    }
