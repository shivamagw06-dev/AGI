"""Orion CFA-Level IC Case Study V2 — held-out 500-point benchmark."""

from __future__ import annotations

from pathlib import Path

from evals.orion_ic_case_study_v2_held_out import (
    CASE_FACTS,
    NEVER_TRAIN,
    QUESTIONS,
    TOTAL_RUBRIC_POINTS,
)
from evals.orion_ic_case_v2_scorecard import build_prompt, run_orion_v2_scorecard, score_item
from institutional_reasoning.engine import package_reasoning_answer
from institutional_reasoning.ic_case_study import detect_ic_case_mode


def test_orion_bank_never_train_and_500_points():
    assert NEVER_TRAIN is True
    assert len(QUESTIONS) == 16
    assert sum(int(q["marks"]) for q in QUESTIONS) == TOTAL_RUBRIC_POINTS == 500
    assert "Orion Global Industries" in CASE_FACTS
    assert "restatement" in CASE_FACTS.lower()
    assert "No Buy/Sell/Hold" in CASE_FACTS


def test_orion_bank_never_imported_by_matchers():
    root = Path(__file__).resolve().parents[1]
    forbidden = (
        "orion_ic_case_study_v2_held_out",
        "ORION RESEARCH DOSSIER V2",
        "Orion Global Industries",
        "Nova Robotics",
        "GreenGrid",
    )
    modules = [
        root / "institutional_reasoning" / "gold_patterns.py",
        root / "institutional_reasoning" / "family_composers.py",
        root / "institutional_reasoning" / "family_classifier.py",
        root / "institutional_reasoning" / "adversarial.py",
        root / "institutional_reasoning" / "ic_case_study.py",
        root / "institutional_reasoning" / "ic_case_study_v2.py",
        root / "institutional_reasoning" / "bias_defense.py",
    ]
    for path in modules:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not contain held-out token {token!r}"


def test_orion_v2_modes_detect():
    assert detect_ic_case_mode(
        "Financial statement analysis: evaluate revenue quality, earnings quality, cash conversion, working capital."
    )["mode"] == "ic_fsa_pack"
    assert detect_ic_case_mode(
        "Credit analysis: interest coverage, debt maturity, liquidity, refinancing risk, covenant pressure, rating outlook."
    )["mode"] == "ic_credit_analysis"
    assert detect_ic_case_mode(
        "Competing investment committees: Committee A growth investors, Committee B value investors, Committee C credit committee."
    )["mode"] == "ic_competing_committees"
    assert detect_ic_case_mode(
        "If every valuation model, analyst report and management presentation were removed, what conclusion could still be supported using only audited financial statements and verified market data?"
    )["mode"] == "ic_audited_only"


def test_orion_v2_scorecard_high_bar():
    report = run_orion_v2_scorecard()
    assert report["ok"] is True
    assert report["never_train"] is True
    assert report["total"] == 16
    assert report["points_possible"] == 500
    assert report["passed"] >= 14, report
    assert report["points_earned"] >= 450, report
    row = score_item(QUESTIONS[0], package_reasoning_answer(build_prompt(QUESTIONS[0])))
    assert row["mode_got"] == "ic_fsa_pack"
