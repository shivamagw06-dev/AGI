"""Institutional Accounting Exam (Level 1) — release-gate acceptance tests.

These tests validate the EXAM ITSELF (every item runs, checks are
computed correctly, the weighted rubric aggregates correctly, and the
release gate is enforced as specified) as well as running the FULL exam
against the actual Phase 1/2 engines and asserting the release gate
passes — this is the concrete Phase 1/2 → Phase 3 gate.
"""

from __future__ import annotations

import pytest

from institutional_accounting_exam import production
from institutional_accounting_exam.all_items import ALL_EXAM_ITEMS, items_by_section
from institutional_accounting_exam.grader import grade_exam, grade_item
from institutional_accounting_exam.schema import PASSING_SCORE, RELEASE_GATE, RUBRIC_WEIGHTS


# ---------------------------------------------------------------------------
# Structural integrity
# ---------------------------------------------------------------------------
def test_exam_has_thirty_items_across_ten_sections():
    assert len(ALL_EXAM_ITEMS) == 30
    sections = {i.section for i in ALL_EXAM_ITEMS}
    assert sections == set("ABCDEFGHIJ")


def test_section_a_through_e_have_five_questions_each():
    for section in "ABCDE":
        assert len(items_by_section(section)) == 5, section


def test_section_f_through_j_have_one_composite_task_each():
    for section in "FGHIJ":
        assert len(items_by_section(section)) == 1, section


def test_every_item_id_is_unique():
    ids = [i.id for i in ALL_EXAM_ITEMS]
    assert len(ids) == len(set(ids))


def test_every_item_runs_without_raising():
    for item in ALL_EXAM_ITEMS:
        answer = item.run()
        assert answer.answer_text
        assert len(answer.answer_text) > 20


# ---------------------------------------------------------------------------
# Section A — accounting correctness must be 100% (deterministic engine)
# ---------------------------------------------------------------------------
def test_section_a_all_accounting_checks_pass():
    for item in items_by_section("A"):
        result = grade_item(item)
        assert result.accounting_score == 1.0, f"{item.id} failed: {result.answer.accounting_checks}"


def test_section_a_journal_entries_are_balanced():
    for item in items_by_section("A"):
        answer = item.run()
        balanced_keys = [k for k in answer.accounting_checks if "balanced" in k]
        assert balanced_keys, item.id
        for k in balanced_keys:
            assert answer.accounting_checks[k] is True, f"{item.id}.{k}"


# ---------------------------------------------------------------------------
# Statement linkage checks (wherever present) must be 100%
# ---------------------------------------------------------------------------
def test_all_linkage_checks_pass_where_present():
    for item in ALL_EXAM_ITEMS:
        result = grade_item(item)
        if result.linkage_score >= 0:
            assert result.linkage_score == 1.0, f"{item.id} linkage failed: {result.answer.linkage_checks}"


# ---------------------------------------------------------------------------
# Interpretation quality
# ---------------------------------------------------------------------------
def test_interpretation_keypoint_coverage_reasonable():
    weak = []
    for item in ALL_EXAM_ITEMS:
        result = grade_item(item)
        if result.interpretation_score >= 0 and result.interpretation_score < 0.5:
            weak.append((item.id, result.interpretation_score))
    assert not weak, f"Items with weak interpretation coverage: {weak}"


def test_every_answer_provides_evidence():
    for item in ALL_EXAM_ITEMS:
        answer = item.run()
        assert answer.evidence, f"{item.id} produced no evidence"


# ---------------------------------------------------------------------------
# Causal reasoning — Section B/C/D/E/I answers must explain WHY
# ---------------------------------------------------------------------------
def test_causal_reasoning_present_across_reasoning_sections():
    for section in "BCDEI":
        for item in items_by_section(section):
            result = grade_item(item)
            assert result.causal_score == 1.0, f"{item.id} lacks causal reasoning"


# ---------------------------------------------------------------------------
# Section J — honesty about uncertainty (release-gate critical)
# ---------------------------------------------------------------------------
def test_section_j_admits_uncertainty_correctly():
    j_items = items_by_section("J")
    assert len(j_items) == 1
    result = grade_item(j_items[0])
    assert result.answer.admits_uncertainty_correctly is True
    assert result.uncertainty_score == 1.0


def test_section_j_detects_naive_overconfident_answers():
    """The exam must prove it can tell the difference between an honest
    'insufficient evidence' answer and a hallucinated single-cause claim."""
    from institutional_accounting_exam.section_fj_composite import _section_j_impossible_questions

    answer = _section_j_impossible_questions()
    for row in answer.evidence["results"]:
        assert row["naive_overconfident_answer_detected"] is True, row["question"]


# ---------------------------------------------------------------------------
# Section G — reconstruction must reconcile exactly against internally
# consistent (real double-entry) data
# ---------------------------------------------------------------------------
def test_section_g_cash_flow_reconstruction_reconciles_exactly():
    result = grade_item(items_by_section("G")[0])
    assert result.accounting_score == 1.0
    assert result.linkage_score == 1.0


# ---------------------------------------------------------------------------
# No hallucinations anywhere in the exam
# ---------------------------------------------------------------------------
def test_zero_hallucinations_across_all_items():
    for item in ALL_EXAM_ITEMS:
        answer = item.run()
        assert answer.hallucination_detected is False, f"{item.id} hallucinated: {answer.hallucination_reason}"


# ---------------------------------------------------------------------------
# Grader / rubric mechanics
# ---------------------------------------------------------------------------
def test_rubric_weights_match_spec_exactly():
    """Accounting 20 / Linkage 20 / Interpretation 25 / Causal 20 / Honesty
    10 = 95% base, with Hallucination penalty -15% applied on top — this is
    the literal weighting from the brief, not a normalized-to-100% rubric.
    A hallucination-free, all-perfect answer set therefore caps at 95%."""
    positive = sum(v for v in RUBRIC_WEIGHTS.values() if v > 0)
    assert positive == pytest.approx(0.95)
    assert RUBRIC_WEIGHTS["hallucination_penalty"] == pytest.approx(-0.15)


def test_grade_exam_produces_all_six_dimensions():
    report = grade_exam(ALL_EXAM_ITEMS)
    expected_dims = {
        "accounting_correctness", "statement_linkage", "interpretation",
        "causal_reasoning", "honesty_about_uncertainty", "hallucination_rate",
    }
    assert set(report.dimension_scores.keys()) == expected_dims
    assert 0.0 <= report.overall_score <= 1.0


def test_perfect_answers_score_maximum():
    """Sanity check the grader math: if every dimension is perfect and there
    are no hallucinations, overall score must equal the rubric's base weight
    sum (95%) — the weights themselves cap the achievable score below 100%,
    by design (see test_rubric_weights_match_spec_exactly)."""
    from institutional_accounting_exam.schema import ExamAnswer, ExamItem

    def _perfect() -> ExamAnswer:
        return ExamAnswer(
            answer_text="Perfect answer with evidence.",
            evidence={"x": 1},
            accounting_checks={"a": True},
            linkage_checks={"b": True},
            interpretation_keypoints_expected=["x"],
            interpretation_keypoints_matched=["x"],
            causal_reasoning_present=True,
            admits_uncertainty_correctly=True,
            hallucination_detected=False,
        )

    items = [ExamItem(f"P{i}", "A", i, "perfect", 1.0, _perfect) for i in range(5)]
    report = grade_exam(items)
    assert report.overall_score == pytest.approx(0.95)
    assert report.passed is True


def test_hallucinating_answers_are_penalized_and_fail_gate():
    from institutional_accounting_exam.schema import ExamAnswer, ExamItem

    def _hallucinated() -> ExamAnswer:
        return ExamAnswer(
            answer_text="A confident but unsupported claim.",
            evidence={},
            accounting_checks={"a": True},
            linkage_checks={"b": True},
            interpretation_keypoints_expected=["x"],
            interpretation_keypoints_matched=["x"],
            causal_reasoning_present=True,
            admits_uncertainty_correctly=False,
            hallucination_detected=True,
            hallucination_reason="fabricated a specific cause without evidence",
        )

    items = [ExamItem(f"H{i}", "A", i, "bad", 1.0, _hallucinated) for i in range(5)]
    report = grade_exam(items)
    assert report.dimension_scores["hallucination_rate"] == 1.0
    assert report.overall_score < 1.0
    assert report.passed is False
    assert report.release_gate["zero_hallucinations_met"] is False


# ---------------------------------------------------------------------------
# THE release gate itself — run the full real exam
# ---------------------------------------------------------------------------
def test_full_exam_meets_release_gate():
    """This is the actual Phase 1/2 -> Phase 3 gate. If this fails, Phase 3
    should not begin."""
    report = grade_exam(ALL_EXAM_ITEMS)

    assert report.overall_score >= PASSING_SCORE, (
        f"Overall score {report.overall_score * 100:.1f}% is below the "
        f"{PASSING_SCORE * 100:.0f}% passing threshold"
    )
    assert report.release_gate["journal_accuracy"] == 1.0, "Journal accuracy must be 100%"
    assert report.release_gate["statement_linkage_accuracy"] == 1.0, "Statement linkage accuracy must be 100%"
    assert report.release_gate["hallucination_rate"] == 0.0, "Hallucination rate must be zero"
    assert report.release_gate["uncertainty_admission_met"] is True
    assert report.passed is True, "Release gate must PASS before Phase 3 begins"


# ---------------------------------------------------------------------------
# Production facade
# ---------------------------------------------------------------------------
def test_production_health():
    h = production.health()
    assert h["status"] == "ok"
    assert h["total_items"] == 30


def test_production_run_full_exam_matches_direct_call():
    out = production.run_full_exam()
    assert out["passed"] is True
    assert out["overall_score"] >= PASSING_SCORE


def test_production_run_item():
    out = production.run_item("Q1")
    assert out["found"] is True
    assert out["accounting_score"] == 1.0
    missing = production.run_item("DOES_NOT_EXIST")
    assert missing["found"] is False
