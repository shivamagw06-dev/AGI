"""Question Understanding Engine v1.1 tests."""

from __future__ import annotations

from question_understanding_engine import (
    QUESTION_TAXONOMY,
    TARGET_TAXONOMY_COUNT,
    apply_question_understanding_engine,
    build_research_brief,
    downstream_contract,
    health,
    validate_research_brief,
)


def test_health_v11():
    h = health()
    assert h["version"] == "1.1"
    assert h["feature"] == "research_brief_generator"


def test_taxonomy_has_500_labeled_questions():
    assert len(QUESTION_TAXONOMY) == TARGET_TAXONOMY_COUNT


def test_tcs_deserve_research_brief_example():
    brief = build_research_brief(
        "Does Tata Consultancy Services deserve research today?",
        ticker="TCS",
        company="Tata Consultancy Services",
    )
    assert brief["decision_type"] == "Research Priority"
    assert "materially" in brief["primary_investment_question"].lower()
    assert "Business Quality" in brief["required_information"]
    assert "Price targets" in brief["irrelevant_information"] or "Technical" in str(brief["irrelevant_information"])
    assert len(brief["top_research_questions"]) == 3
    assert brief["response_promise"]
    assert len(brief["success_criteria"]) >= 3
    assert validate_research_brief(brief)["passed"] is True


def test_should_i_buy_tcs_brief():
    brief = build_research_brief("Should I buy TCS?", ticker="TCS")
    assert brief["decision_type"] == "Capital Allocation"
    assert "rather than another opportunity" in brief["primary_investment_question"]
    assert brief["knowledge_gap"]
    assert "valuation" in brief["knowledge_gap"].lower() or "returns" in brief["knowledge_gap"].lower()


def test_downstream_contract():
    brief = build_research_brief("Why is Titan expensive?")
    contract = downstream_contract(brief)
    assert contract["research_workflow"]["required_information"]
    assert len(contract["evidence_graph"]["focus_questions"]) == 3
    assert contract["response_planner"]["response_promise"]


def test_apply_wires_research_brief():
    out = apply_question_understanding_engine(
        {},
        query="Does Tata Consultancy Services deserve research today?",
        ticker="TCS",
    )
    que = out["question_understanding_engine"]
    assert que["version"] == "1.1"
    assert out["research_brief"]["decision_type"] == "Research Priority"
    assert out["downstream_contract"]
    assert out["intent_resolution"]["que_v1_1"] is True
    assert out["top_research_questions"]


def test_brief_validation_fails_incomplete():
    assert validate_research_brief({})["passed"] is False
