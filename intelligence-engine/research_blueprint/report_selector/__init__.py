"""Report selector — choose optimal report type for the question."""

from __future__ import annotations

from typing import Any


OBJECTIVE_TO_REPORT: dict[str, str] = {
    "investment evaluation": "institutional_investment_report",
    "decision_support": "institutional_investment_report",
    "peer comparison": "comparison_report",
    "comparison_assessment": "comparison_report",
    "educational": "educational_guide",
    "educational_explanation": "educational_guide",
    "historical analysis": "historical_valuation_report",
    "valuation_assessment": "historical_valuation_report",
    "macro impact": "macro_intelligence_report",
    "forecast_assessment": "forecast_report",
    "portfolio decision": "portfolio_memorandum",
    "portfolio_assessment": "portfolio_memorandum",
    "risk assessment": "risk_report",
    "risk_assessment": "risk_report",
    "accounting review": "accounting_review",
    "management assessment": "management_review",
    "forecast": "forecast_report",
    "scenario analysis": "scenario_analysis",
    "screening": "screening_report",
    "news impact": "news_brief",
    "monitoring_update": "news_brief",
    "business quality assessment": "company_research_report",
    "financial health assessment": "company_research_report",
    "sector attractiveness": "sector_research_report",
    "industry structure": "industry_report",
    "technical analysis": "market_open_brief",
    "fact_retrieval": "news_brief",
    "opportunity_assessment": "institutional_investment_report",
}


def _infer_from_question(question: str) -> str | None:
    q = question.lower()
    if "explain" in q or "what is" in q or "define" in q or "teach" in q or "means" in q:
        return "educational_guide"
    if "compare" in q or " vs " in q or " versus " in q:
        return "comparison_report"
    if "expensive versus history" in q or "versus history" in q or "historical percentile" in q:
        return "historical_valuation_report"
    if "stress test" in q or "stress-test" in q:
        return "stress_test"
    if "scenario" in q and ("bull" in q or "bear" in q or "base" in q or "analysis" in q):
        return "scenario_analysis"
    if "portfolio" in q or "allocate" in q or "₹" in q or "rs" in q:
        return "portfolio_memorandum"
    if "committee" in q or "ic memo" in q:
        return "investment_committee_memo"
    if "accounting" in q:
        return "accounting_review"
    if "management" in q and ("assess" in q or "review" in q or "quality" in q):
        return "management_review"
    if "rbi" in q or "macro" in q or "inflation" in q or "rate cut" in q or "policy" in q:
        return "macro_intelligence_report"
    if "risk" in q:
        return "risk_report"
    if "forecast" in q or "earnings" in q and "will" in q:
        return "forecast_report"
    if "screen" in q:
        return "screening_report"
    if "market open" in q or "pre-market" in q or "premarket" in q:
        return "market_open_brief"
    if "market close" in q or "end of day" in q or "eod" in q:
        return "market_close_brief"
    if "news" in q or "headline" in q:
        return "news_brief"
    if "sector" in q and ("attractive" in q or "outlook" in q):
        return "sector_research_report"
    if "industry" in q:
        return "industry_report"
    if "overvalued" in q or "undervalued" in q or "pe" in q and "history" in q:
        return "historical_valuation_report"
    if "buy" in q or "sell" in q or "should i" in q:
        return "institutional_investment_report"
    if "company" in q or "business quality" in q:
        return "company_research_report"
    return None


def select_report_type(
    *,
    question: str,
    primary_objective: str | None = None,
    intent_family: str | None = None,
) -> dict[str, Any]:
    obj = (primary_objective or "").strip().lower()
    family = (intent_family or "").strip().lower()
    q = question.lower()

    # Strong lexical signals win over coarse objective labels
    strong = None
    strong_reason = ""
    if "stress test" in q or "stress-test" in q:
        strong, strong_reason = "stress_test", "Strong signal: stress test"
    elif "explain" in q or "what is" in q or "define" in q or "teach" in q:
        strong, strong_reason = "educational_guide", "Strong signal: educational"
    elif "compare" in q or " vs " in q or " versus " in q:
        if "history" in q and "expensive" in q:
            strong, strong_reason = "historical_valuation_report", "Strong signal: historical valuation"
        else:
            strong, strong_reason = "comparison_report", "Strong signal: comparison"
    elif "expensive versus history" in q or "versus history" in q:
        strong, strong_reason = "historical_valuation_report", "Strong signal: historical valuation"
    elif "market open" in q or "pre-market" in q or "premarket" in q:
        strong, strong_reason = "market_open_brief", "Strong signal: market open"
    elif "market close" in q:
        strong, strong_reason = "market_close_brief", "Strong signal: market close"

    if strong:
        return {
            "report_type": strong,
            "selection_reason": strong_reason,
            "primary_objective": obj or None,
            "intent_family": family or None,
        }

    report_type = OBJECTIVE_TO_REPORT.get(obj)
    reason = f"Mapped from primary_objective={obj}" if report_type else ""

    if not report_type:
        report_type = _infer_from_question(question)
        reason = "Inferred from question text" if report_type else ""

    if not report_type:
        if family == "educational":
            report_type = "educational_guide"
        elif family == "macro":
            report_type = "macro_intelligence_report"
        elif family == "portfolio":
            report_type = "portfolio_memorandum"
        elif family == "sector":
            report_type = "sector_research_report"
        else:
            report_type = "institutional_investment_report"
        reason = f"Fallback from intent_family={family or 'company'}"

    return {
        "report_type": report_type,
        "selection_reason": reason,
        "primary_objective": obj or None,
        "intent_family": family or None,
    }
