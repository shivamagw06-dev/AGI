"""Deterministic templates — no phrase variation, no randomness."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_reporting.recommendation import business_quality_band, normalize_recommendation


def _bullets(rows: Sequence[str]) -> str:
    items = [str(r).strip() for r in rows if str(r).strip()]
    if not items:
        return "- (none supplied)\n"
    return "".join(f"- {item}\n" for item in items)


def institutional_view_body(inp: Any) -> str:
    rec = normalize_recommendation(inp.recommendation)
    return (
        f"Institutional View\n\n"
        f"Recommendation\n\n"
        f"{rec}\n\n"
        f"Conviction\n\n"
        f"{str(inp.conviction).strip().upper()}\n\n"
        f"Company\n\n"
        f"{inp.company_name} ({inp.ticker})\n\n"
        f"Sector\n\n"
        f"{inp.sector}\n"
    )


def investment_horizon_body(inp: Any) -> str:
    return f"Investment Horizon\n\n{inp.horizon}\n"


def investment_thesis_body(inp: Any) -> str:
    return "Investment Thesis\n\n" + _bullets(inp.thesis)


def business_quality_body(inp: Any) -> str:
    band = business_quality_band(inp.business_quality)
    score = inp.business_quality
    score_line = f"Score: {score}\n\n" if isinstance(score, (int, float)) else ""
    reasons = list(inp.business_quality_reasons) or list(inp.thesis[:1])
    reason_text = "; ".join(reasons) if reasons else "structured quality inputs"
    return (
        f"Business Quality\n\n"
        f"{score_line}"
        f"Assessment: {band}\n\n"
        f"Business quality remains {band.lower()} because\n"
        f"{reason_text}.\n"
    )


def financial_quality_body(inp: Any) -> str:
    label = str(inp.financial_quality).strip()
    reasons = list(inp.financial_quality_reasons) or [f"financial quality marked {label}"]
    reason_text = "; ".join(reasons)
    return (
        f"Financial Quality\n\n"
        f"Assessment: {label}\n\n"
        f"Financial quality appears {label.lower()} because\n"
        f"{reason_text}.\n"
    )


def valuation_body(inp: Any) -> str:
    label = str(inp.valuation).strip().title()
    reasons = list(inp.valuation_reasons) or [f"valuation marked {label}"]
    reason_text = "; ".join(reasons)
    verb = "appears"
    return (
        f"Valuation\n\n"
        f"Assessment: {label}\n\n"
        f"Valuation {verb} {label.lower()} because\n"
        f"{reason_text}.\n"
    )


def risk_assessment_body(inp: Any) -> str:
    label = str(inp.overall_risk).strip().title()
    reasons = list(inp.risk_reasons) or list(inp.risks[:2]) or [f"overall risk marked {label}"]
    reason_text = "; ".join(reasons)
    return (
        f"Risk Assessment\n\n"
        f"Overall Risk: {label}\n\n"
        f"Risk remains {label.lower()} because\n"
        f"{reason_text}.\n\n"
        f"Key Risks\n\n"
        f"{_bullets(inp.risks)}"
    )


def bull_case_body(inp: Any) -> str:
    points = list(inp.bull_points) or list(inp.catalysts) or list(inp.thesis[:2])
    return "Bull Case\n\n" + _bullets(points)


def bear_case_body(inp: Any) -> str:
    points = list(inp.bear_points) or list(inp.risks[:3])
    return "Bear Case\n\n" + _bullets(points)


def watch_items_body(inp: Any) -> str:
    return "Watch Items\n\n" + _bullets(inp.watch_items)


def evidence_section_body(inp: Any) -> str:
    lines = ["Evidence", ""]
    if not inp.evidence:
        lines.append("(none)")
        return "\n".join(lines) + "\n"
    for item in inp.evidence:
        lines.append(item.evidence_id)
        lines.append(item.label)
        if item.source_type:
            lines.append(item.source_type)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def bottom_line_body(inp: Any) -> str:
    rec = normalize_recommendation(inp.recommendation)
    return (
        f"Bottom Line\n\n"
        f"The institutional stance on {inp.company_name} is {rec} "
        f"with {str(inp.conviction).strip().upper()} conviction and "
        f"{int(inp.confidence)}% confidence over a {inp.horizon} horizon.\n"
    )
