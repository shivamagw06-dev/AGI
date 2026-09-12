from institutional_evaluation_lab.datasets.catalog import catalog_stats, load_suite
from institutional_evaluation_lab.judges.economic_reasoning import evaluate_answer, evaluate_industry_models
from institutional_evaluation_lab.production import cre_investment_benchmark

def test_suite_has_four_questions_for_every_canonical_industry():
    rows = load_suite("cre_investment_144")
    assert len(rows) == 144
    assert len({x["sector"] for x in rows}) == 36
    assert all(sum(y["sector"] == x for y in rows) == 4 for x in {y["sector"] for y in rows})
    assert catalog_stats()["cre_investment_144"] == 144

def test_economic_evaluator_requires_all_four_epistemic_layers():
    answer = {"evidence": ["E1"], "why": ["A -> B"], "financial_transmission": ["A -> B"],
              "evidence_gaps": ["valuation"], "bear_case": ["B fails"], "what_changes_view": ["B reverses"],
              "monitoring": ["B"], "direct_conclusion": ["Monitor"], "confidence": "MEDIUM",
              "decision_relevance": "NO_MATERIAL_CHANGE",
              "epistemic_layers": {"evidence": [], "interpretation": [], "scenario": [], "thesis": []}}
    out = evaluate_answer(answer)
    assert out["passed"] and out["overall"] == 10
    del answer["epistemic_layers"]["scenario"]
    assert "epistemic_separation" in evaluate_answer(answer)["missing"]

def test_all_industry_models_are_measured_without_inventing_38():
    out = evaluate_industry_models()
    assert out["industry_count"] == 36 and len(out["rows"]) == 36
    assert 0 <= out["mean_score"] <= 10
    assert cre_investment_benchmark()["question_count"] == 144
