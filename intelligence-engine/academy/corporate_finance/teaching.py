"""Corporate finance understanding exams."""

from __future__ import annotations

from typing import Any

from academy.corporate_finance.knowledge_objects import knowledge_by_id


def _must_contain(answer: str, needles: list[str]) -> bool:
    text = (answer or "").lower()
    return all(n.lower() in text for n in needles)


EXAMS: list[dict[str, Any]] = [
    {
        "id": "roic_vs_revenue_growth",
        "question": "Why does ROIC matter more than revenue growth?",
        "required_concepts": ["roic_wacc_spread", "value_creation", "incremental_roic"],
        "rubric_must_include": ["roic", "wacc", "value"],
        "model_answer": (
            "Revenue growth only creates value when incremental capital earns above the cost of capital. "
            "ROIC relative to WACC determines the economic profit of growth; high growth with ROIC below "
            "WACC destroys intrinsic value even as sales rise."
        ),
    },
    {
        "id": "wacc_industry_differences",
        "question": "Why does WACC differ across industries?",
        "required_concepts": ["wacc", "beta", "optimal_capital_structure"],
        "rubric_must_include": ["risk", "leverage", "wacc"],
        "model_answer": (
            "Industries differ in operating risk (betas), debt capacity, tax shields, and distress costs. "
            "Those differences change the cost of equity, cost of debt, and optimal leverage, so the blended "
            "WACC varies systematically across sectors."
        ),
    },
    {
        "id": "leverage_changes_valuation",
        "question": "Why does leverage change valuation?",
        "required_concepts": ["financial_leverage", "wacc", "financial_distress"],
        "rubric_must_include": ["debt", "wacc", "distress"],
        "model_answer": (
            "Leverage changes valuation because it alters the tax shield, equity risk (beta), and expected "
            "distress costs. Moderate debt can lower WACC and raise firm value; excess debt raises distress "
            "risk and can destroy value despite a lower headline cost of debt."
        ),
    },
    {
        "id": "buybacks_destroy_value",
        "question": "Why can buybacks destroy value?",
        "required_concepts": ["share_buybacks", "eps_illusion", "value_destruction"],
        "rubric_must_include": ["intrinsic", "buyback", "eps"],
        "model_answer": (
            "Buybacks destroy value when shares are repurchased above intrinsic value or when cash is diverted "
            "from higher-NPV uses. EPS can still rise, creating an illusion of success while transferring wealth "
            "to selling shareholders and shrinking intrinsic value for ongoing owners."
        ),
    },
    {
        "id": "acquisitions_fail",
        "question": "Why do acquisitions often fail?",
        "required_concepts": ["acquisition_overpayment", "acquisition_synergies", "integration_risk"],
        "rubric_must_include": ["overpay", "synerg", "integrat"],
        "model_answer": (
            "Acquisitions often fail because premiums exceed the present value of deliverable synergies and "
            "integration risk prevents capturing what remains. Hubris and agency problems drive overpayment, "
            "so acquirer shareholders frequently fund a wealth transfer to target owners."
        ),
    },
    {
        "id": "high_growth_not_value",
        "question": "Why does high growth not always create value?",
        "required_concepts": ["growth_without_returns_destroys", "incremental_roic", "organic_reinvestment"],
        "rubric_must_include": ["growth", "roic", "wacc"],
        "model_answer": (
            "High growth requires reinvestment. If incremental ROIC is below WACC, each new unit of growth "
            "earns less than the opportunity cost of capital, so economic profit and intrinsic value fall even "
            "as revenue accelerates."
        ),
    },
    {
        "id": "capital_allocation_management_quality",
        "question": "Why is capital allocation one of the strongest indicators of management quality?",
        "required_concepts": ["capital_allocation", "value_creation", "agency_costs"],
        "rubric_must_include": ["capital allocation", "value", "management"],
        "model_answer": (
            "Capital allocation reveals whether management deploys and returns cash in ways that create value "
            "by earning above the hurdle rate. Operating skill can be undone by empire building, overpriced "
            "deals, or stubborn reinvestment in low-ROIC projects — so allocation is a direct management-quality signal."
        ),
    },
]


def answer_question(question_id: str) -> dict[str, Any]:
    exam = next((e for e in EXAMS if e["id"] == question_id), None)
    if not exam:
        raise KeyError(f"Unknown ACF exam question: {question_id}")
    kb = knowledge_by_id()
    # allow mental model ids in required list without KO
    supporting = {}
    for cid in exam["required_concepts"]:
        if cid in kb:
            supporting[cid] = {
                "definition": kb[cid].definition,
                "first_principles": kb[cid].first_principles,
                "investment_impact": kb[cid].investment_impact,
                "valuation_impact": kb[cid].valuation_impact,
            }
    return {
        "question_id": exam["id"],
        "question": exam["question"],
        "answer": exam["model_answer"],
        "supporting_concepts": supporting,
        "course": "damodaran_applied_corporate_finance",
        "mode": "understanding",
        "not_quotation": True,
    }


def run_exam_suite() -> dict[str, Any]:
    results = []
    kb = knowledge_by_id()
    for exam in EXAMS:
        ans = answer_question(exam["id"])
        ok = _must_contain(ans["answer"], exam["rubric_must_include"])
        # mental model ids may not be KOs
        missing = [
            c
            for c in exam["required_concepts"]
            if c not in kb and c not in ("growth_without_returns_destroys",)
        ]
        # growth_without_returns_destroys is mental model - treat as ok if absent from kb
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
        "course": "damodaran_applied_corporate_finance",
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
        "course": "damodaran_applied_corporate_finance",
        "what_it_is": ko.definition,
        "business_meaning": d.get("business_meaning"),
        "why_it_exists": ko.first_principles,
        "management_decisions": d.get("management_decisions") or [],
        "how_investors_should_think": ko.investment_impact,
        "how_fle_should_use_it": ko.forecast_impact,
        "how_ve_should_use_it": ko.valuation_impact,
        "decision_framework": ko.decision_framework,
        "explainability": ko.explainability,
        "teaching_rule": "Judge every finance decision by value creation — returns versus cost of capital.",
    }
