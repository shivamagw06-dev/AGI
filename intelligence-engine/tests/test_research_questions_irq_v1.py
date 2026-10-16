"""RQ2 Sprint 2 — Institutional Research Question Engine regression tests."""

from research_questions.production import generate_for_question, quality_gates, soft_slice_for_ask_agi
from research_questions.quality_rules import evaluate_question_quality
from research_questions.schema import (
    MIN_CONTRADICTION_QUESTIONS,
    MIN_HISTORICAL_QUESTIONS,
    MIN_PEER_QUESTIONS,
    MIN_QUESTIONS_PER_HYPOTHESIS,
    QUALITY_RULES,
)


def test_hdfc_funding_hypothesis_questions():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    assert row["ok"] is True
    assert row["hypothesis_count"] >= 2
    assert row["research_question_count"] >= MIN_QUESTIONS_PER_HYPOTHESIS * 2
    block = row["hypothesis_question_sets"][0]
    cov = block["coverage"]
    assert cov["question_count"] >= MIN_QUESTIONS_PER_HYPOTHESIS
    assert cov["contradiction_count"] >= MIN_CONTRADICTION_QUESTIONS
    assert cov["historical_count"] >= MIN_HISTORICAL_QUESTIONS
    assert cov["peer_count"] >= MIN_PEER_QUESTIONS
    assert cov["meets_minima"] is True
    assert (block.get("question_tree") or {}).get("proof_chain")
    assert (block.get("question_tree") or {}).get("edges")


def test_nifty_valuation_questions():
    row = generate_for_question("Is Nifty IT expensive versus history?", {})
    texts = " ".join(q["question"].lower() for q in row["research_questions"])
    assert "percentile" in texts or "premium" in texts or "historical" in texts
    for q in row["research_questions"]:
        assert q["analyst_owner"]
        assert q["required_evidence"]
        assert q["decision_impact"] is not None
        assert 1 <= int(q["decision_impact"]) <= 10


def test_rejects_generic_question():
    bad = evaluate_question_quality("Tell me about the company", required_evidence=[])
    assert bad["passed"] is False
    good = evaluate_question_quality(
        "Has HDFC's CASA ratio remained above peer median during the last ten years?",
        required_evidence=["FIL", "PIL"],
    )
    assert good["passed"] is True


def test_output_contract_and_ownership():
    row = generate_for_question("Compare TCS vs Infosys", {})
    q0 = row["research_questions"][0]
    for key in (
        "question",
        "priority",
        "analyst_owner",
        "required_evidence",
        "dependencies",
        "status",
        "confidence",
        "decision_impact",
    ):
        assert key in q0
    owners = {q["analyst_owner"] for q in row["research_questions"]}
    assert owners  # at least one owner assigned
    assert all(isinstance(q["analyst_owner"], str) and q["analyst_owner"] for q in row["research_questions"])


def test_decision_impact_prioritises_critical():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    critical = [q for q in row["research_questions"] if q["priority"] == "Critical"]
    assert critical
    assert all(int(q["decision_impact"]) >= 8 for q in critical)


def test_soft_slice_ask_agi():
    wrap = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})
    body = wrap["research_questions"]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["executes_after"] == "IHG / Hypothesis Generation"
    assert body["executes_before"] == "Evidence Collection"
    assert body["research_question_count"] >= MIN_QUESTIONS_PER_HYPOTHESIS
    assert body["enhancements"]["question_tree"] is True
    assert body["enhancements"]["decision_impact_score"] is True
    assert body["five_quality_rules"] == list(QUALITY_RULES)


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 500
    assert gates["research_questions_generated"] >= 10_000
    assert gates["question_relevance"] >= 1.0
    assert gates["question_quality"] >= 1.0
    assert gates["question_uniqueness"] >= 1.0
    assert gates["evidence_mapping"] >= 1.0
    assert gates["analyst_ownership"] >= 1.0
    assert gates["coverage"] >= 1.0
    assert gates["avg_generation_ms"] < 40
    assert gates["ok"] is True
