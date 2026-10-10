"""Module 14 — Concept Examination: item bank integrity + deterministic grading."""

from __future__ import annotations

import pytest

from financial_concepts.exam import CONCEPT_EXAM, grade_answer, list_exam_questions, run_item

ALL_ITEM_IDS = [i.item_id for i in CONCEPT_EXAM]


def test_exam_has_at_least_150_items():
    assert len(CONCEPT_EXAM) >= 150


def test_exam_item_ids_are_unique():
    assert len(ALL_ITEM_IDS) == len(set(ALL_ITEM_IDS))


@pytest.mark.parametrize("item_id", ALL_ITEM_IDS)
def test_every_item_runs_to_a_grounded_model_answer(item_id):
    result = run_item(item_id)
    assert result["found"], f"{item_id} failed to produce a model answer"
    assert result["model_answer"].strip()
    assert result["fabricated"] is False
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.parametrize("item_id", ALL_ITEM_IDS)
def test_every_item_grades_its_own_model_answer_as_passing(item_id):
    """The exam's own model answer must pass its own grader — otherwise the
    exam is internally inconsistent."""

    model = run_item(item_id)
    grade = grade_answer(item_id, model["model_answer"])
    assert grade["found"]
    assert grade["hallucination_flagged"] is False
    assert grade["total_score"] >= 50, f"{item_id} model answer scored only {grade['total_score']}/100"


def test_unknown_item_id_not_found():
    assert run_item("CE-999999")["found"] is False
    assert grade_answer("CE-999999", "anything")["found"] is False


def test_hallucinated_answer_is_flagged_and_fails():
    grade = grade_answer("CE-001", "XYZ Quantum Robotics Pvt Ltd always does this without exception.")
    assert grade["hallucination_flagged"] is True
    assert grade["passed"] is False


def test_empty_answer_scores_zero_reasoning():
    grade = grade_answer("CE-001", "")
    assert grade["scores"]["explicit_uncertainty"] == 0
    assert grade["passed"] is False


def test_hedged_language_scores_higher_uncertainty_than_absolute_claims():
    hedged = grade_answer("CE-001", "This usually happens because debt typically rises relative to cash.")
    absolute = grade_answer("CE-001", "This always happens because debt never falls.")
    assert hedged["scores"]["explicit_uncertainty"] >= absolute["scores"]["explicit_uncertainty"]


def test_list_exam_questions_filters_by_section():
    all_q = list_exam_questions()
    assert all_q["n"] == len(CONCEPT_EXAM)
    valuation_q = list_exam_questions("Valuation")
    assert valuation_q["n"] > 0
    assert all(q["section"] == "Valuation" for q in valuation_q["items"])


def test_hand_authored_brief_examples_present():
    prompts = {i.prompt for i in CONCEPT_EXAM}
    assert any("Why is Enterprise Value larger than Market Cap" in p for p in prompts)
    assert any("Why is ROIC more useful than ROE" in p for p in prompts)
    assert any("Why do banks trade on Price-to-Book" in p for p in prompts)
    assert any("Explain the DuPont Model" in p for p in prompts)
    assert any("Why can Free Cash Flow Yield exceed Earnings Yield" in p for p in prompts)
    assert any("What happens" in p and "WACC" in p and "ROIC" in p for p in prompts)
    assert any("What does Economic Profit measure" in p for p in prompts)
