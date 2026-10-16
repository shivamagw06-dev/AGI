"""Plain-English editorial templates — glossary-backed, never advice."""

from __future__ import annotations

from typing import Any

from editorial.glossary import plain_english, simplify_jargon


def _company(structured: dict[str, Any]) -> str:
    return str(structured.get("company") or "The company").strip() or "The company"


def _quality_phrase(structured: dict[str, Any]) -> str:
    bq = structured.get("business_quality")
    fq = structured.get("financial_quality")
    bits = []
    if bq:
        bits.append(
            "strong and reliable business strength"
            if str(bq).lower() in {"excellent", "strong", "a", "a+", "high"}
            else f"business strength rated {bq}"
        )
    if fq:
        bits.append(
            "stable financial health"
            if str(fq).lower() in {"stable", "strong", "good"}
            else f"financial health rated {fq}"
        )
    if not bits:
        return "steady business and financial health"
    if len(bits) == 1:
        return bits[0]
    return f"{bits[0]} and {bits[1]}"


def template_quick_summary(structured: dict[str, Any], question: str | None = None) -> str:
    company = _company(structured)
    reasons = list(structured.get("top_reasons") or [])
    risks = list(structured.get("top_risks") or [])
    val = structured.get("valuation")

    if (
        str(structured.get("investment_thesis_status") or "").upper() == "INCONCLUSIVE"
        or str(structured.get("evidence_insufficient") or "").lower() == "true"
    ):
        risk = simplify_jargon(str(risks[0]).rstrip(".")) if risks else "important evidence is still missing"
        return plain_english(
            f"AGIB does not yet have enough verified evidence to form a firm view on {company}; "
            "that is an incomplete assessment, not a negative judgment on the business. "
            f"The main issue to resolve is {risk}."
        )

    s1 = f"{company} continues to show {_quality_phrase(structured)}."
    if reasons:
        evidence = simplify_jargon(str(reasons[0]).rstrip("."))
        s2 = f"{evidence}."
    elif val:
        s2 = (
            f"Current market price compared with the company's performance "
            f"is described as {val} in the available assessment."
        )
    else:
        s2 = "The available evidence is limited, so the picture is incomplete."

    if risks:
        risk = simplify_jargon(str(risks[0]).rstrip("."))
        if risk:
            risk = risk[0].lower() + risk[1:]
        s3 = f"The main point to watch is {risk}."
    else:
        s3 = "Available evidence is insufficient to highlight a clear risk."

    return plain_english(f"{s1} {s2} {s3}".strip())


def template_quick_analysis(structured: dict[str, Any], question: str | None = None) -> str:
    base = template_quick_summary(structured, question=question)
    reasons = list(structured.get("top_reasons") or [])
    extra = ""
    if len(reasons) > 1:
        extra = f" Another supporting point is {simplify_jargon(str(reasons[1]).rstrip('.'))}."
    return plain_english(f"{base}{extra}".strip())


def template_detailed_analysis(structured: dict[str, Any], question: str | None = None) -> str:
    company = _company(structured)
    base = template_quick_analysis(structured, question=question)
    bq = structured.get("business_quality")
    fq = structured.get("financial_quality")
    val = structured.get("valuation")
    horizon = structured.get("investment_horizon")
    extras = []
    if bq or fq:
        extras.append(
            f"In simple terms, how strong and reliable {company}'s business is"
            + (f" is rated {bq}" if bq else "")
            + (" and " if bq and fq else " ")
            + (f"financial health is {fq}" if fq else "")
            + "."
        )
    if val:
        extras.append(
            "Current market price compared with the company's performance "
            f"is labelled {val} in the supplied assessment."
        )
    if horizon:
        extras.append(f"The time frame noted in the assessment is {horizon}.")
    reasons = list(structured.get("top_reasons") or [])
    for reason in reasons[:3]:
        extras.append(simplify_jargon(str(reason).rstrip(".")) + ".")
    risks = list(structured.get("top_risks") or [])
    for risk in risks[:2]:
        extras.append("A key limitation is " + simplify_jargon(str(risk).rstrip(".")) + ".")
    if not reasons and not risks:
        extras.append("Available evidence is insufficient for a denser explanation.")
    body = " ".join(extras)
    return plain_english(f"{base} {body}".strip())


def render_template(mode: str, structured: dict[str, Any], question: str | None = None) -> str:
    if mode == "detailed_analysis":
        return template_detailed_analysis(structured, question=question)
    if mode == "quick_analysis":
        return template_quick_analysis(structured, question=question)
    return template_quick_summary(structured, question=question)
