"""Financial statement / key metric extraction from tables + text."""

from __future__ import annotations

from typing import Any

from filing_intelligence.schema import ExtractedFact

FINANCIAL_METRICS = {
    "PAT",
    "NII",
    "NIM",
    "ROE",
    "ROA",
    "ROIC",
    "CET1",
    "CAR",
    "GNPA",
    "CASA",
    "Deposits_YoY",
    "Time_deposits_YoY",
    "CASA_deposits_YoY",
    "Credit_Cost",
    "Revenue_Growth",
    "Operating_Margin",
    "EBIT_Margin",
    "Free_Cash_Flow",
    "Capex",
    "Debt",
    "Cash",
}


def extract_statements(parsed: dict[str, Any]) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    ticker = str(parsed.get("ticker") or "")
    doc_id = str(parsed.get("doc_id") or "")
    default_period = str(parsed.get("period") or "")
    tier = int(parsed.get("evidence_tier") or 5)

    for table in parsed.get("tables") or []:
        tname = table.get("name") or "table"
        for i, row in enumerate(table.get("rows") or []):
            metric = str(row.get("metric") or "")
            if metric not in FINANCIAL_METRICS and metric not in {
                "PAT",
                "NII",
                "NIM",
                "CASA",
                "CET1",
                "ROE",
                "ROA",
                "GNPA",
                "CAR",
                "Credit_Cost",
                "Revenue_Growth",
                "Deposits_YoY",
                "Time_deposits_YoY",
                "CASA_deposits_YoY",
            }:
                continue
            period = str(row.get("period") or default_period)
            value = row.get("value")
            if value is None:
                continue
            facts.append(
                ExtractedFact(
                    fact_id=f"{doc_id}:{metric}:{period}:{i}",
                    ticker=ticker,
                    metric=metric,
                    value=value,
                    unit=str(row.get("unit") or ""),
                    period=period,
                    doc_id=doc_id,
                    section=tname,
                    page=row.get("page"),
                    evidence_tier=tier,
                    confidence=0.95 if tier <= 2 else 0.85,
                    validation_status=_status(parsed, row),
                    category="financial",
                )
            )
    return _dedupe(facts)


def _status(parsed: dict[str, Any], row: dict[str, Any]) -> str:
    meta = parsed.get("metadata") if isinstance(parsed.get("metadata"), dict) else {}
    # metadata may live on original doc — parser doesn't always pass it; default verified for table rows
    if row.get("unit") in (None, ""):
        return "needs_review"
    if meta and meta.get("validation") == "partially_verified":
        return "partially_verified"
    return "verified"


def _dedupe(facts: list[ExtractedFact]) -> list[ExtractedFact]:
    seen: set[str] = set()
    out: list[ExtractedFact] = []
    for f in facts:
        key = f"{f.ticker}|{f.metric}|{f.period}|{f.value}"
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out
