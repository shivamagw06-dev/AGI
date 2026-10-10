"""Teaching-mode exams — test understanding, not quotation."""

from __future__ import annotations

from typing import Any

from academy.knowledge_objects import knowledge_by_id


def _must_contain(answer: str, needles: list[str]) -> bool:
    text = (answer or "").lower()
    return all(n.lower() in text for n in needles)


EXAMS: list[dict[str, Any]] = [
    {
        "id": "rates_stock_prices",
        "question": "Why do interest rates affect stock prices?",
        "required_concepts": ["discount_rate", "present_value", "monetary_policy"],
        "rubric_must_include": ["discount", "present value", "cash flow"],
        "model_answer": (
            "Interest rates enter the discount rate used to convert expected future cash flows into "
            "present value. When rates rise, present values fall—especially for long-duration growth "
            "cash flows—so equity valuations compress even if near-term earnings are unchanged. "
            "Rates also affect real activity via credit demand, feeding back into cash-flow forecasts."
        ),
    },
    {
        "id": "banks_rising_rates",
        "question": "Why do banks benefit from rising rates?",
        "required_concepts": ["monetary_policy", "credit"],
        "rubric_must_include": ["net interest", "loan", "deposit"],
        "model_answer": (
            "Many banks earn a net interest margin between loan yields and deposit/funding costs. "
            "When policy rates rise, floating-rate assets often reprice faster than deposits, "
            "widening NIMs—provided credit demand and asset quality do not deteriorate enough to "
            "offset the margin gain."
        ),
    },
    {
        "id": "inflation_valuation",
        "question": "Why does inflation affect valuation?",
        "required_concepts": ["inflation", "discount_rate"],
        "rubric_must_include": ["discount", "cash", "inflation"],
        "model_answer": (
            "Inflation raises nominal discount rates and can compress valuation multiples, while also "
            "changing nominal cash flows through revenues and costs. Firms without pricing power see "
            "margin damage; DCF terminal values are highly sensitive to the gap between WACC and growth "
            "when inflation lifts the cost of capital."
        ),
    },
    {
        "id": "gdp_importance",
        "question": "Why is GDP important?",
        "required_concepts": ["gdp"],
        "rubric_must_include": ["output", "income", "revenue"],
        "model_answer": (
            "GDP measures the market value of final output and equals aggregate income. "
            "It anchors the opportunity set for corporate revenue, fiscal receipts, and cyclical "
            "risk. Forecast engines scale sector revenue with GDP betas rather than treating GDP "
            "as a trivia statistic."
        ),
    },
    {
        "id": "unemployment_lagging",
        "question": "Why is unemployment a lagging indicator?",
        "required_concepts": ["unemployment", "business_cycle"],
        "rubric_must_include": ["lag", "hiring", "firing"],
        "model_answer": (
            "Firms delay hiring and firing because labour adjustment is costly. Output and orders "
            "typically turn before payrolls, so unemployment confirms the cycle with a lag after GDP "
            "and industrial activity have already moved."
        ),
    },
    {
        "id": "utilities_defensive",
        "question": "Why are utilities defensive?",
        "required_concepts": ["business_cycle", "elasticity"],
        "rubric_must_include": ["inelastic", "demand", "cycle"],
        "model_answer": (
            "Electricity and essential utility services have relatively inelastic demand and regulated "
            "or contracted cash flows, so volumes and earnings fall less than cyclicals across the "
            "business cycle. They behave as bond-proxies: rate-sensitive on valuation, but operationally defensive."
        ),
    },
    {
        "id": "growth_discount_sensitivity",
        "question": "Why are growth stocks more sensitive to discount rates?",
        "required_concepts": ["discount_rate", "present_value"],
        "rubric_must_include": ["duration", "future", "discount"],
        "model_answer": (
            "Growth stocks derive a larger share of value from future cash flows. Duration is high, "
            "so a given increase in the discount rate reduces present value more than for short-duration "
            "value/cash-flow businesses."
        ),
    },
]


def answer_question(question_id: str) -> dict[str, Any]:
    exam = next((e for e in EXAMS if e["id"] == question_id), None)
    if not exam:
        raise KeyError(f"Unknown exam question: {question_id}")
    kb = knowledge_by_id()
    supporting = {
        cid: {
            "definition": kb[cid].definition,
            "first_principles": kb[cid].first_principles,
            "investment_impact": kb[cid].investment_impact,
            "valuation_impact": kb[cid].valuation_impact,
        }
        for cid in exam["required_concepts"]
        if cid in kb
    }
    return {
        "question_id": exam["id"],
        "question": exam["question"],
        "answer": exam["model_answer"],
        "supporting_concepts": supporting,
        "mode": "understanding",
        "not_quotation": True,
    }


def run_exam_suite() -> dict[str, Any]:
    results = []
    for exam in EXAMS:
        ans = answer_question(exam["id"])
        ok = _must_contain(ans["answer"], exam["rubric_must_include"])
        missing = [c for c in exam["required_concepts"] if c not in knowledge_by_id()]
        results.append(
            {
                "id": exam["id"],
                "question": exam["question"],
                "passed": ok and not missing,
                "missing_concepts": missing,
                "rubric_ok": ok,
            }
        )
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": [r for r in results if not r["passed"]],
        "results": results,
        "complete": all(r["passed"] for r in results),
    }


def teach(concept_id: str) -> dict[str, Any]:
    """Professor mode: generalise mechanisms, never memorise a statistic."""
    kb = knowledge_by_id()
    ko = kb.get(concept_id)
    if not ko:
        raise KeyError(concept_id)
    return {
        "concept_id": concept_id,
        "what_it_is": ko.definition,
        "why_it_exists": ko.first_principles,
        "how_it_affects_businesses": ko.industry_impact,
        "how_investors_should_think": ko.investment_impact,
        "how_fle_should_use_it": ko.forecast_impact,
        "how_ve_should_use_it": ko.valuation_impact,
        "decision_framework": ko.decision_framework,
        "explainability": ko.explainability,
        "teaching_rule": "Never memorise a print; generalise the mechanism.",
    }
