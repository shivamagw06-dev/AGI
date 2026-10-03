"""Governance events from filings."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact


def extract_governance(parsed: dict[str, Any]) -> list[ExtractedFact]:
    text = (parsed.get("text") or "").lower()
    hits = []
    for label, needle in [
        ("Board_Meeting", "board meeting"),
        ("Governance_Report", "corporate governance"),
        ("Dividend_Policy", "dividend policy"),
    ]:
        if needle in text:
            hits.append(label)
    if not hits:
        return []
    return [
        ExtractedFact(
            fact_id=f"{parsed.get('doc_id')}:gov:{label}",
            ticker=str(parsed.get("ticker") or ""),
            metric=label,
            value=True,
            unit="",
            period=str(parsed.get("period") or ""),
            doc_id=str(parsed.get("doc_id") or ""),
            section="governance",
            evidence_tier=int(parsed.get("evidence_tier") or 5),
            confidence=0.7,
            validation_status="partially_verified",
            category="governance",
        )
        for label in hits
    ]
