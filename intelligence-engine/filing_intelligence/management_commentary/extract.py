"""Management commentary — store every quarter, never overwrite."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact

THEMES = [
    ("Management_Outlook", ("outlook", "expect", "gradual")),
    ("Key_Priorities", ("priorities", "rebuild", "resilience")),
    ("Growth_Drivers", ("growth", "loan growth", "premiumisation", "volume")),
    ("Pricing_Commentary", ("pricing", "deposit-cost", "funding-cost")),
    ("Demand_Commentary", ("demand",)),
    ("Margin_Commentary", ("nim", "margin")),
    ("Competitive_Commentary", ("competitive",)),
    ("Macro_Commentary", ("interest-rate", "inflation", "macro")),
    ("Capital_Allocation_Plans", ("capital allocation", "organic growth", "brand investment")),
]


def extract_management(parsed: dict[str, Any]) -> list[ExtractedFact]:
    text = (parsed.get("sections") or {}).get("management") or parsed.get("text") or ""
    lower = text.lower()
    facts: list[ExtractedFact] = []
    doc_id = str(parsed.get("doc_id") or "")
    for i, (metric, needles) in enumerate(THEMES):
        if any(n in lower for n in needles):
            facts.append(
                ExtractedFact(
                    fact_id=f"{doc_id}:mgmt:{metric}:{i}",
                    ticker=str(parsed.get("ticker") or ""),
                    metric=metric,
                    value=_snippet(text, needles[0]),
                    unit="",
                    period=str(parsed.get("period") or ""),
                    doc_id=doc_id,
                    section="management",
                    evidence_tier=int(parsed.get("evidence_tier") or 5),
                    confidence=0.8,
                    validation_status="verified" if int(parsed.get("evidence_tier") or 5) <= 2 else "partially_verified",
                    category="management",
                )
            )
    return facts


def _snippet(text: str, needle: str) -> str:
    lower = text.lower()
    idx = lower.find(needle)
    if idx < 0:
        return text[:180]
    return text[max(0, idx - 30) : idx + 140].strip()
