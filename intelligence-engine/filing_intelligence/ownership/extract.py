"""Ownership / shareholding extraction."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact

OWN_KEYS = [
    ("Promoter_Holdings", ("promoter",)),
    ("Institutional_Holdings", ("institutional", "fii", "dii")),
    ("Foreign_Holdings", ("foreign holdings", "fii")),
    ("Mutual_Funds", ("mutual fund",)),
    ("Insiders", ("insider",)),
    ("Shareholding_Changes", ("shareholding",)),
]


def extract_ownership(parsed: dict[str, Any]) -> list[ExtractedFact]:
    if parsed.get("doc_type") not in {"shareholding_filing", "annual_report", "governance_report"}:
        # only extract if keywords present
        text = (parsed.get("text") or "").lower()
        if "shareholding" not in text and "promoter" not in text:
            return []
    text = parsed.get("text") or ""
    lower = text.lower()
    facts: list[ExtractedFact] = []
    doc_id = str(parsed.get("doc_id") or "")
    for i, (metric, needles) in enumerate(OWN_KEYS):
        if any(n in lower for n in needles):
            facts.append(
                ExtractedFact(
                    fact_id=f"{doc_id}:own:{metric}:{i}",
                    ticker=str(parsed.get("ticker") or ""),
                    metric=metric,
                    value=True,
                    unit="",
                    period=str(parsed.get("period") or ""),
                    doc_id=doc_id,
                    section="ownership",
                    evidence_tier=int(parsed.get("evidence_tier") or 5),
                    confidence=0.7,
                    validation_status="needs_review",
                    category="ownership",
                )
            )
    return facts
