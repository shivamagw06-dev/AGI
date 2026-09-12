"""Risk register extraction — current / historical / newly added / removed."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact

RISK_MAP = [
    ("Business_Risk", ("competitive", "demand", "franchise")),
    ("Financial_Risk", ("funding", "nim", "credit cost", "interest-rate")),
    ("Regulatory_Risk", ("regulatory", "rbi", "sebi")),
    ("Technology_Risk", ("cyber", "technology")),
    ("Competition_Risk", ("competitive intensity", "competition")),
    ("Supply_Chain_Risk", ("supply chain", "commodity")),
    ("Execution_Risk", ("integration", "execution", "merger")),
    ("Geopolitical_Risk", ("geopolitical",)),
]


def extract_risks(parsed: dict[str, Any]) -> list[ExtractedFact]:
    text = (parsed.get("sections") or {}).get("risks") or parsed.get("text") or ""
    lower = text.lower()
    facts: list[ExtractedFact] = []
    doc_id = str(parsed.get("doc_id") or "")
    for i, (metric, needles) in enumerate(RISK_MAP):
        if any(n in lower for n in needles):
            facts.append(
                ExtractedFact(
                    fact_id=f"{doc_id}:risk:{metric}:{i}",
                    ticker=str(parsed.get("ticker") or ""),
                    metric=metric,
                    value=next(n for n in needles if n in lower),
                    unit="",
                    period=str(parsed.get("period") or ""),
                    doc_id=doc_id,
                    section="risks",
                    evidence_tier=int(parsed.get("evidence_tier") or 5),
                    confidence=0.78,
                    validation_status="partially_verified",
                    category="risk",
                    notes="status=current",
                )
            )
    return facts


def risk_register(facts: list[dict[str, Any]]) -> dict[str, Any]:
    risks = [f for f in facts if f.get("category") == "risk"]
    by_metric: dict[str, list[dict[str, Any]]] = {}
    for r in risks:
        by_metric.setdefault(r["metric"], []).append(r)
    current = sorted({r["metric"] for r in risks})
    return {
        "current": current,
        "historical": by_metric,
        "newly_added": [],  # requires prior snapshot diff — reserved
        "removed": [],
        "count": len(risks),
    }
