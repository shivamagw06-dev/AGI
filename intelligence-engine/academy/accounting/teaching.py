"""Accounting understanding exams — investor reasoning, not quotation."""

from __future__ import annotations

from typing import Any

from academy.accounting.knowledge_objects import knowledge_by_id


def _must_contain(answer: str, needles: list[str]) -> bool:
    text = (answer or "").lower()
    return all(n.lower() in text for n in needles)


EXAMS: list[dict[str, Any]] = [
    {
        "id": "profit_vs_cash",
        "question": "Why do profit and cash flow differ?",
        "required_concepts": ["net_income", "operating_cash_flow", "accruals"],
        "rubric_must_include": ["accrual", "working capital", "cash"],
        "model_answer": (
            "Profit is an accrual measure that recognises revenues and expenses when earned/incurred, "
            "while cash flow records cash movements. Timing differences in working capital, non-cash "
            "charges, and estimates create the gap between net income and operating cash flow."
        ),
    },
    {
        "id": "ebitda_not_cash",
        "question": "Why is EBITDA not cash flow?",
        "required_concepts": ["ebitda", "free_cash_flow"],
        "rubric_must_include": ["capex", "working capital", "cash"],
        "model_answer": (
            "EBITDA adds back depreciation/amortisation but still ignores working capital cash needs, "
            "taxes, and especially capex required to maintain and grow the asset base. Free cash flow "
            "subtracts reinvestment; EBITDA does not, so it is not cash flow."
        ),
    },
    {
        "id": "working_capital_matters",
        "question": "Why does working capital matter?",
        "required_concepts": ["working_capital", "free_cash_flow"],
        "rubric_must_include": ["cash", "growth", "working capital"],
        "model_answer": (
            "Working capital funds the operating cycle. Growth typically consumes cash through higher "
            "receivables and inventory even when profits rise. Changes in working capital therefore "
            "directly alter free cash flow and intrinsic value."
        ),
    },
    {
        "id": "aggressive_revenue",
        "question": "How does aggressive revenue recognition inflate earnings?",
        "required_concepts": ["revenue_recognition", "accounts_receivable", "earnings_quality"],
        "rubric_must_include": ["revenue", "receivable", "cash"],
        "model_answer": (
            "Pulling revenue forward books sales before cash is collected or before performance "
            "obligations are fully met. Receivables rise, reported earnings inflate, and cash lags — "
            "until reversals, allowances, or restatements unwind the exaggeration."
        ),
    },
    {
        "id": "goodwill_impairments",
        "question": "Why do goodwill impairments occur?",
        "required_concepts": ["goodwill", "impairment", "roic"],
        "rubric_must_include": ["acquisition", "value", "impairment"],
        "model_answer": (
            "Goodwill records the premium paid in an acquisition over identifiable net assets. When "
            "expected synergies or growth fail and the unit's recoverable value falls below carrying "
            "value, accounting requires an impairment charge — often lagging the economic value loss."
        ),
    },
    {
        "id": "cash_conversion_matters",
        "question": "Why does cash conversion matter?",
        "required_concepts": ["earnings_quality", "operating_cash_flow"],
        "rubric_must_include": ["cash", "earnings", "quality"],
        "model_answer": (
            "Cash conversion shows whether accounting earnings turn into operating cash. Weak or "
            "falling conversion means earnings quality is poor, forecasts are less reliable, and "
            "valuation multiples should compress until cash catches up."
        ),
    },
    {
        "id": "accounting_quality_valuation",
        "question": "How does accounting quality affect valuation?",
        "required_concepts": ["earnings_quality", "free_cash_flow"],
        "rubric_must_include": ["discount", "cash", "margin of safety"],
        "model_answer": (
            "Low accounting quality raises uncertainty about persistent cash flows, so investors "
            "increase discount rates or required margin of safety and haircut multiples. High-quality, "
            "cash-backed earnings support tighter discounts and more confidence in DCF inputs."
        ),
    },
]


def answer_question(question_id: str) -> dict[str, Any]:
    exam = next((e for e in EXAMS if e["id"] == question_id), None)
    if not exam:
        raise KeyError(f"Unknown accounting exam question: {question_id}")
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
        "course": "damodaran_minimalist_accounting",
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
        "course": "damodaran_minimalist_accounting",
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": [r for r in results if not r["passed"]],
        "results": results,
        "complete": all(r["passed"] for r in results),
    }


def teach(concept_id: str) -> dict[str, Any]:
    kb = knowledge_by_id()
    ko = kb.get(concept_id)
    if not ko:
        raise KeyError(concept_id)
    d = ko.to_dict()
    return {
        "concept_id": concept_id,
        "course": "damodaran_minimalist_accounting",
        "what_it_is": ko.definition,
        "business_meaning": d.get("business_meaning"),
        "accounting_meaning": d.get("accounting_meaning"),
        "why_it_exists": ko.first_principles,
        "how_investors_should_think": ko.investment_impact,
        "how_fle_should_use_it": ko.forecast_impact,
        "how_ve_should_use_it": ko.valuation_impact,
        "red_flags": d.get("red_flags") or [],
        "decision_framework": ko.decision_framework,
        "explainability": ko.explainability,
        "teaching_rule": "Read statements as an investor — generalise mechanisms, never memorise a line item.",
    }
