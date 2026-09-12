"""Filing parser — normalize document into parse tree for extractors."""

from __future__ import annotations

from typing import Any

from filing_intelligence.ingestion.detect import detect_doc_type


def parse_document(doc: dict[str, Any]) -> dict[str, Any]:
    detected = detect_doc_type(
        title=str(doc.get("title") or ""),
        text=str(doc.get("text") or ""),
        hint=doc.get("doc_type"),
    )
    text = str(doc.get("text") or "")
    sections = _split_sections(text)
    return {
        "doc_id": doc.get("doc_id"),
        "ticker": doc.get("ticker"),
        "period": doc.get("period"),
        "as_of": doc.get("as_of"),
        "url": doc.get("url"),
        "evidence_tier": doc.get("evidence_tier", 5),
        "doc_type": detected["doc_type"],
        "detection": detected,
        "sections": sections,
        "tables": list(doc.get("tables") or []),
        "text": text,
        "source_publisher": doc.get("source_publisher"),
        "title": doc.get("title"),
    }


def _split_sections(text: str) -> dict[str, str]:
    keys = {
        "management": ("management", "priorities", "outlook"),
        "guidance": ("guidance", "expect", "medium-term"),
        "risks": ("risk", "pressure", "competitive"),
        "capital": ("capital allocation", "buyback", "dividend", "cet1 buffer"),
        "notes": ("accounting", "exceptional", "goodwill", "related party", "contingent"),
        "segments": ("segment", "retail", "wholesale", "confectionery"),
    }
    lower = text.lower()
    out: dict[str, str] = {}
    for name, needles in keys.items():
        if any(n in lower for n in needles):
            out[name] = text
    out.setdefault("body", text)
    return out
