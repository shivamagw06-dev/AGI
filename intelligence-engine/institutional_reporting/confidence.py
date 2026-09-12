"""Confidence explanation — always explain the number."""

from __future__ import annotations

from typing import Any

from institutional_reporting.models import InstitutionalReportInput


def _as_fact_list(value: Any) -> list[str]:
    """Normalize tuple/list/str fact fields — never iterate a bare string by character."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def explain_confidence(inp: InstitutionalReportInput) -> dict[str, Any]:
    """Return structured confidence block with mandatory drivers."""
    positive = _as_fact_list(inp.positive_drivers)
    negative = _as_fact_list(inp.negative_drivers)
    unknowns = _as_fact_list(inp.unknowns)

    # Deterministic fallbacks derived from structured facts when drivers omitted.
    if not positive:
        if isinstance(inp.business_quality, (int, float)) and float(inp.business_quality) >= 70:
            positive.append(f"Business quality score {inp.business_quality}")
        if str(inp.financial_quality).strip():
            positive.append(f"Financial quality assessed as {inp.financial_quality}")
        if str(inp.valuation).strip().title() in {"Cheap", "Fair"}:
            positive.append(f"Valuation assessed as {str(inp.valuation).strip().title()}")
        for point in inp.thesis[:2]:
            positive.append(point)

    if not negative:
        if str(inp.overall_risk).strip().title() in {"High", "Severe"}:
            negative.append(f"Overall risk assessed as {str(inp.overall_risk).strip().title()}")
        if str(inp.valuation).strip().title() == "Expensive":
            negative.append("Valuation assessed as Expensive")
        for risk in inp.risks[:2]:
            negative.append(risk)

    if not unknowns:
        unknowns.append("Forward estimates not fully verified in this report package")
        if not inp.catalysts:
            unknowns.append("Near-term catalysts not supplied")

    # Deduplicate while preserving order
    def _dedupe(rows: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for row in rows:
            key = row.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    positive = _dedupe(positive) or ["No positive drivers supplied"]
    negative = _dedupe(negative) or ["No negative drivers supplied"]
    unknowns = _dedupe(unknowns) or ["No unknowns supplied"]

    lines = [
        "Confidence",
        "",
        f"{int(inp.confidence)}%",
        "",
        "Positive Drivers",
        "",
        *[f"- {p}" for p in positive],
        "",
        "Negative Drivers",
        "",
        *[f"- {n}" for n in negative],
        "",
        "Unknowns",
        "",
        *[f"- {u}" for u in unknowns],
    ]
    return {
        "score": int(inp.confidence),
        "positive_drivers": positive,
        "negative_drivers": negative,
        "unknowns": unknowns,
        "body": "\n".join(lines).strip() + "\n",
    }
