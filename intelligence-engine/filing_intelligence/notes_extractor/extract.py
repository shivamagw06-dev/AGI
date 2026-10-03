"""Accounting notes extraction."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact

NOTE_PATTERNS = [
    ("Revenue_Recognition", "revenue recognition"),
    ("Accounting_Policy_Change", "accounting policy"),
    ("Contingent_Liabilities", "contingent"),
    ("Legal_Proceedings", "legal proceeding"),
    ("One_off_Items", "one-off"),
    ("Exceptional_Items", "exceptional"),
    ("Deferred_Tax", "deferred tax"),
    ("Related_Party", "related party"),
    ("Lease_Accounting", "lease"),
    ("Goodwill", "goodwill"),
    ("Impairments", "impairment"),
]


def extract_notes(parsed: dict[str, Any]) -> list[ExtractedFact]:
    text = (parsed.get("sections") or {}).get("notes") or parsed.get("text") or ""
    lower = text.lower()
    facts: list[ExtractedFact] = []
    ticker = str(parsed.get("ticker") or "")
    doc_id = str(parsed.get("doc_id") or "")
    period = str(parsed.get("period") or "")
    tier = int(parsed.get("evidence_tier") or 5)
    for i, (metric, needle) in enumerate(NOTE_PATTERNS):
        if needle in lower:
            # capture short clause
            idx = lower.find(needle)
            snippet = text[max(0, idx - 40) : idx + 120].strip()
            facts.append(
                ExtractedFact(
                    fact_id=f"{doc_id}:note:{metric}:{i}",
                    ticker=ticker,
                    metric=metric,
                    value=snippet or needle,
                    unit="",
                    period=period,
                    doc_id=doc_id,
                    section="notes",
                    evidence_tier=tier,
                    confidence=0.75,
                    validation_status="partially_verified",
                    category="note",
                )
            )
    return facts
