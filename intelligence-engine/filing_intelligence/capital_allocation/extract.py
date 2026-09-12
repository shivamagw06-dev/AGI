"""Capital allocation engine — what and why."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact

ALLOC_MAP = [
    ("Dividends", ("dividend",)),
    ("Buybacks", ("buyback",)),
    ("Acquisitions", ("acquisition", "merger")),
    ("Organic_Investment", ("organic growth", "brand investment", "distribution")),
    ("Capex", ("capex",)),
    ("Debt_Reduction", ("debt reduction", "delever")),
    ("Cash_Build", ("cash build", "liquidity")),
    ("Capital_Raises", ("capital raise", "qip", "fpo")),
    ("Capital_Buffer", ("cet1 buffer", "balance-sheet resilience", "capital remains strong")),
]


def extract_capital_allocation(parsed: dict[str, Any]) -> list[ExtractedFact]:
    text = (parsed.get("sections") or {}).get("capital") or parsed.get("text") or ""
    lower = text.lower()
    facts: list[ExtractedFact] = []
    doc_id = str(parsed.get("doc_id") or "")
    why = ""
    if "resilience" in lower:
        why = "Management prioritised balance-sheet resilience"
    elif "organic" in lower:
        why = "Management preferred organic investment over extraordinary distribution"
    elif "brand investment" in lower:
        why = "Management allocated capital to brand and distribution"
    for i, (metric, needles) in enumerate(ALLOC_MAP):
        if any(n in lower for n in needles):
            facts.append(
                ExtractedFact(
                    fact_id=f"{doc_id}:capalloc:{metric}:{i}",
                    ticker=str(parsed.get("ticker") or ""),
                    metric=metric,
                    value=True,
                    unit="",
                    period=str(parsed.get("period") or ""),
                    doc_id=doc_id,
                    section="capital_allocation",
                    evidence_tier=int(parsed.get("evidence_tier") or 5),
                    confidence=0.8,
                    validation_status="partially_verified",
                    category="capital",
                    notes=why or "Capital allocation action referenced in filing",
                )
            )
    if why:
        facts.append(
            ExtractedFact(
                fact_id=f"{doc_id}:capalloc:why",
                ticker=str(parsed.get("ticker") or ""),
                metric="Allocation_Rationale",
                value=why,
                unit="",
                period=str(parsed.get("period") or ""),
                doc_id=doc_id,
                section="capital_allocation",
                evidence_tier=int(parsed.get("evidence_tier") or 5),
                confidence=0.75,
                validation_status="partially_verified",
                category="capital",
            )
        )
    return facts
