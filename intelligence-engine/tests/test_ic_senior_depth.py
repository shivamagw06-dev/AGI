"""Senior IC depth — close the diagnose-vs-quantify gap."""

from __future__ import annotations

from pathlib import Path

from evals.ic_senior_depth_held_out import NEVER_TRAIN, QUESTIONS, TOTAL_RUBRIC_POINTS
from evals.ic_senior_depth_scorecard import run_senior_depth_scorecard
from institutional_reasoning.ic_case_study import detect_ic_case_mode


def test_depth_bank_never_train():
    assert NEVER_TRAIN is True
    assert len(QUESTIONS) == 9
    assert TOTAL_RUBRIC_POINTS == 180


def test_depth_bank_never_imported_by_matchers():
    root = Path(__file__).resolve().parents[1]
    forbidden = ("ic_senior_depth_held_out", "Nova Dynamics")
    for rel in (
        "institutional_reasoning/gold_patterns.py",
        "institutional_reasoning/family_composers.py",
        "institutional_reasoning/adversarial.py",
        "institutional_reasoning/ic_case_study.py",
        "institutional_reasoning/ic_case_study_v2.py",
        "institutional_reasoning/ic_case_study_depth.py",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{rel} must not contain {token}"


def test_depth_modes_detect():
    assert detect_ic_case_mode(
        "Estimate ROIC and estimate WACC; quantify value destruction; temporary or structural?"
    )["mode"] == "ic_quant_value_creation"
    assert detect_ic_case_mode(
        "Which assumptions create the biggest valuation sensitivity? WACC +1%, terminal growth −1%."
    )["mode"] == "ic_valuation_sensitivity"
    assert detect_ic_case_mode(
        "Bank-grade credit: debt maturity ladder, interest coverage, liquidity runway, refinancing probability."
    )["mode"] == "ic_bank_grade_credit"
    assert detect_ic_case_mode(
        "Oil +44%: second-order effects through inflation, discount rates, working capital and credit quality."
    )["mode"] == "ic_second_order_macro"


def test_senior_depth_scorecard_high_bar():
    report = run_senior_depth_scorecard()
    assert report["ok"] is True
    assert report["points_possible"] == 180
    assert report["passed"] == 9, report
    assert report["points_earned"] == 180, report
    assert "perfect_on_this_senior_depth_set_9_of_9" in report["claim_discipline"]
