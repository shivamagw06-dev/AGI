"""Document identification — type, exchange, standard hints."""

from __future__ import annotations

from typing import Any


def identify_document(data: bytes, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = dict(meta or {})
    head = (data or b"")[:200].lstrip()
    doc_type = str(meta.get("document_type") or "unknown").lower()

    if doc_type == "unknown" or not doc_type:
        if head.startswith(b"%PDF"):
            doc_type = "pdf"
        elif head.startswith(b"{") or head.startswith(b"["):
            doc_type = "json"
        elif head.startswith(b"<"):
            lower = head[:80].lower()
            if b"xbrl" in lower or b"xmlns" in lower:
                doc_type = "xbrl"
            else:
                doc_type = "html" if b"html" in lower else "xml"
        elif b"," in head and b"\n" in head:
            doc_type = "csv"
        else:
            doc_type = "unknown"

    return {
        "document_type": doc_type,
        "filing_type": meta.get("filing_type") or meta.get("period_type") or "unknown",
        "exchange": (meta.get("exchange") or "NSE").upper(),
        "reporting_standard": (meta.get("reporting_standard") or "IND_AS").upper(),
        "bytes_len": len(data or b""),
        "layer": "document_identification",
    }
