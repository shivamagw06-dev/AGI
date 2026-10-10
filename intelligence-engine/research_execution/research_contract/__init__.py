"""Research Contract — internal contract before execution begins."""

from __future__ import annotations

from typing import Any


def build_research_contract(
    *,
    question: str,
    intent: dict[str, Any],
    entity: dict[str, Any],
    analyst_plan: dict[str, Any],
    blueprint: dict[str, Any],
) -> dict[str, Any]:
    obj = (
        intent.get("research_objective")
        or intent.get("primary_intent")
        or "Institutional research evaluation"
    )
    name = entity.get("canonical_name") or entity.get("ticker") or "the subject"
    family = str(intent.get("intent_family") or intent.get("decision_type") or "company").lower()
    report = blueprint.get("report_type") or ""

    if "educational" in family or report == "educational_guide" or "explain" in question.lower():
        return {
            "objective": f"Teach {question} with institutional clarity.",
            "must_answer": [
                "Is the definition precise?",
                "Is the calculation correct?",
                "What are common mistakes?",
                "What case study reinforces understanding?",
            ],
            "must_not": [
                "Recommend buy/sell",
                "Discuss portfolio construction",
                "Use unsupported claims",
                "Produce generic filler",
            ],
            "success_definition": (
                "The guide should leave a portfolio manager able to apply the concept correctly."
            ),
            "minimum_evidence": 2,
            "minimum_peer_comparisons": 0,
            "minimum_historical_coverage_years": 0,
            "maximum_unsupported_claims": 0,
            "maximum_hallucinations": 0,
            "required_internal_debate": list(analyst_plan.get("required_analysts") or ["Academy", "Financial"])[:4],
            "committee_must_resolve_disagreements": False,
        }

    if "compare" in question.lower() or report == "comparison_report":
        return {
            "objective": f"Determine the relative institutional attractiveness in: {question}",
            "must_answer": [
                "Which business is stronger?",
                "Which financials are stronger?",
                "Which valuation is more attractive?",
                "What competitive position differences matter?",
                "What evidence supports each conclusion?",
            ],
            "must_not": [
                "Recommend based on momentum",
                "Discuss technical indicators",
                "Use unsupported claims",
                "Ignore contradictory evidence",
                "Produce generic statements",
            ],
            "success_definition": (
                "The comparison should enable a clearer relative allocation decision."
            ),
            "minimum_evidence": 10,
            "minimum_peer_comparisons": 2,
            "minimum_historical_coverage_years": 5,
            "maximum_unsupported_claims": 0,
            "maximum_hallucinations": 0,
            "required_internal_debate": list(
                analyst_plan.get("required_analysts") or ["Business", "Financial", "Valuation", "Sector"]
            )[:5],
            "committee_must_resolve_disagreements": False,
        }

    if (
        "versus history" in question.lower()
        or "historical" in family
        or report == "historical_valuation_report"
        or "historical analysis" in str(intent.get("research_objective") or "").lower()
    ):
        return {
            "objective": f"Determine whether valuation is expensive or attractive versus history for: {question}",
            "must_answer": [
                "Where does current valuation sit versus history?",
                "What percentiles matter?",
                "What do peers imply?",
                "What macro drivers affect the multiple?",
                "What is priced in?",
            ],
            "must_not": [
                "Recommend based on momentum",
                "Discuss unrelated business narrative as primary proof",
                "Use unsupported claims",
                "Ignore contradictory evidence",
            ],
            "success_definition": (
                "The report should clarify whether history and peers support a valuation decision."
            ),
            "minimum_evidence": 8,
            "minimum_peer_comparisons": 5,
            "minimum_historical_coverage_years": 10,
            "maximum_unsupported_claims": 0,
            "maximum_hallucinations": 0,
            "required_internal_debate": list(
                analyst_plan.get("required_analysts") or ["Valuation", "Sector", "Macro", "Forecast"]
            )[:5],
            "committee_must_resolve_disagreements": False,
        }

    if "portfolio" in family or "portfolio" in question.lower():
        return {
            "objective": f"Construct or assess a portfolio decision for: {question}",
            "must_answer": [
                "What risk budget is implied?",
                "Does the construction improve risk-adjusted quality?",
                "What constraints bind?",
                "What evidence supports sizing?",
            ],
            "must_not": [
                "Ignore risk tolerance",
                "Use unsupported return guarantees",
                "Recommend based on momentum alone",
            ],
            "success_definition": (
                "The memo should improve portfolio construction quality versus the prior state."
            ),
            "minimum_evidence": 6,
            "minimum_peer_comparisons": 3,
            "minimum_historical_coverage_years": 5,
            "maximum_unsupported_claims": 0,
            "maximum_hallucinations": 0,
            "required_internal_debate": list(
                analyst_plan.get("required_analysts") or ["Portfolio", "Risk", "Macro"]
            )[:4],
            "committee_must_resolve_disagreements": True,
        }

    # Default institutional investment contract
    return {
        "objective": f"Determine whether {name} is an attractive long-term investment.",
        "must_answer": [
            "Is the business exceptional?",
            "Do financials support the thesis?",
            "Is valuation attractive?",
            "What is priced into the stock?",
            "What would invalidate the thesis?",
            "Does it improve the portfolio?",
            "What evidence supports each conclusion?",
        ],
        "must_not": [
            "Recommend based on momentum",
            "Discuss technical indicators",
            "Use unsupported claims",
            "Ignore contradictory evidence",
            "Produce generic statements",
        ],
        "success_definition": (
            "The report should enable an institutional portfolio manager "
            "to make a better investment decision than before reading it."
        ),
        "minimum_evidence": 12,
        "minimum_peer_comparisons": 5,
        "minimum_historical_coverage_years": 10,
        "maximum_unsupported_claims": 0,
        "maximum_hallucinations": 0,
        "required_internal_debate": list(
            analyst_plan.get("required_analysts")
            or ["Business", "Financial", "Valuation", "Risk"]
        )[:6],
        "committee_must_resolve_disagreements": True,
        "source_question": question,
        "primary_objective": obj,
    }
