"""Blueprint validator — correct report, owners, sections, no irrelevant."""

from __future__ import annotations

from typing import Any


def validate_blueprint(
    *,
    question: str,
    research_blueprint: dict[str, Any] | None = None,
    primary_objective: str | None = None,
) -> dict[str, Any]:
    q = (question or "").lower()
    bp = research_blueprint or {}
    obj = (primary_objective or "").lower()

    report_type = bp.get("report_type")
    mandatory = list(bp.get("mandatory_sections") or [])
    suppressed = set(bp.get("suppressed_sections") or [])
    owners = bp.get("section_owner") or {}
    order = list(bp.get("section_order") or [])

    issues: list[str] = []
    score = 0.7  # baseline when blueprint absent (soft-wire still allows readiness with inference)

    expected = None
    if "explain" in q or "educational" in obj:
        expected = "educational_guide"
    elif "compare" in q or " vs " in q:
        expected = "comparison_report"
    elif "versus history" in q or "expensive versus history" in q:
        expected = "historical_valuation_report"
    elif "portfolio" in q:
        expected = "portfolio_memorandum"
    elif "rbi" in q or "macro" in obj:
        expected = "macro_intelligence_report"
    elif "should i buy" in q or "should i sell" in q or "investment evaluation" in obj:
        expected = "institutional_investment_report"

    if report_type:
        score = 0.9
        if expected and report_type != expected:
            # allow close variants
            if not (expected in report_type or report_type in (expected or "")):
                issues.append("report_type_mismatch")
                score -= 0.25
        if not order:
            issues.append("missing_section_order")
            score -= 0.2
        if mandatory and any(s in suppressed for s in mandatory):
            issues.append("irrelevant_mandatory")
            score -= 0.3
        if order and owners:
            missing_owners = [s for s in order if not owners.get(s)]
            if missing_owners:
                issues.append("missing_owners")
                score -= 0.2
        else:
            if order and not owners:
                issues.append("missing_owners")
                score -= 0.15
        # educational must suppress portfolio/committee
        if report_type == "educational_guide" or expected == "educational_guide":
            for bad in ("portfolio_fit", "committee_opinion", "valuation"):
                if bad in mandatory or (bad in order and bad not in suppressed):
                    # only flag if blueprint present and wrong
                    if report_type == "educational_guide" and bad in order and bad not in suppressed:
                        issues.append("irrelevant_sections")
                        score -= 0.25
                        break
    else:
        # Infer soft blueprint quality from question
        if expected:
            score = 0.75
        issues.append("blueprint_not_provided")

    score = max(0.0, min(1.0, score))
    if "irrelevant_mandatory" in issues or "irrelevant_sections" in issues:
        status = "invalid"
    elif issues and report_type:
        status = "warning"
    elif report_type:
        status = "valid"
    else:
        status = "inferred"

    return {
        "status": status,
        "score": round(score, 4),
        "issues": issues,
        "report_type": report_type or expected,
        "expected_report_type": expected,
        "mandatory_count": len(mandatory),
        "section_count": len(order),
    }
