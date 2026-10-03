"""IRE-02 Reason Composer — Facts → Reason graph (before rendering)."""

from __future__ import annotations

from institutional_reporting import explanation
from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.reasoning import Reason, ReasonGraph
from institutional_reporting.schema import REPORT_SECTIONS

# Section key → explanation function (structured Reason only).
_EXPLAINERS = {
    "institutional_view": explanation.explain_recommendation,
    "investment_horizon": explanation.explain_horizon,
    "confidence": explanation.explain_confidence_section,
    "investment_thesis": explanation.explain_thesis,
    "business_quality": explanation.explain_business_quality,
    "financial_quality": explanation.explain_financial_quality,
    "valuation": explanation.explain_valuation,
    "risk_assessment": explanation.explain_risk,
    "bull_case": explanation.explain_bull_case,
    "bear_case": explanation.explain_bear_case,
    "watch_items": explanation.explain_watch_items,
    "evidence": explanation.explain_evidence_section,
    "bottom_line": explanation.explain_bottom_line,
}


def compose_reasons(inp: InstitutionalReportInput) -> ReasonGraph:
    """Build one Reason per fixed report section — deterministic, no LLM."""
    reasons: list[Reason] = []
    for key in REPORT_SECTIONS:
        fn = _EXPLAINERS[key]
        reason = fn(inp)
        # Enforce section_key alignment even if explainer omits it.
        if reason.section_key != key:
            reason = Reason(
                title=reason.title,
                conclusion=reason.conclusion,
                confidence=reason.confidence,
                supporting_evidence=reason.supporting_evidence,
                supporting_points=reason.supporting_points,
                contradicting_points=reason.contradicting_points,
                unknowns=reason.unknowns,
                section_key=key,
            )
        reasons.append(reason)
    return ReasonGraph(reasons=reasons)
