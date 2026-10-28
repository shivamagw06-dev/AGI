"""Segment intelligence extraction."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact

SEGMENT_HINTS = (
    "retail",
    "wholesale",
    "treasury",
    "prepared dishes",
    "milk products",
    "confectionery",
    "beverages",
    "geographic",
)


def extract_segments(parsed: dict[str, Any]) -> list[ExtractedFact]:
    text = (parsed.get("sections") or {}).get("segments") or parsed.get("text") or ""
    lower = text.lower()
    found = [h for h in SEGMENT_HINTS if h in lower]
    if not found:
        return []
    return [
        ExtractedFact(
            fact_id=f"{parsed.get('doc_id')}:segments",
            ticker=str(parsed.get("ticker") or ""),
            metric="Business_Segments",
            value=", ".join(found),
            unit="",
            period=str(parsed.get("period") or ""),
            doc_id=str(parsed.get("doc_id") or ""),
            section="segments",
            evidence_tier=int(parsed.get("evidence_tier") or 5),
            confidence=0.7,
            validation_status="partially_verified",
            category="segment",
            notes="Segment labels detected from filing commentary; mix tables pending full parse",
        )
    ]
