"""Project Atlas IC case study — held-out evaluation + soft IC habits."""

from __future__ import annotations

from pathlib import Path

from evals.project_atlas_ic_case_study_held_out import (
    CASE_FACTS,
    NEVER_TRAIN,
    QUESTIONS,
    TOTAL_RUBRIC_POINTS,
)
from evals.project_atlas_ic_scorecard import build_prompt, run_project_atlas_scorecard, score_item
from institutional_reasoning.engine import package_reasoning_answer
from institutional_reasoning.ic_case_study import detect_ic_case_mode


def test_atlas_bank_never_train_and_200_points():
    assert NEVER_TRAIN is True
    assert len(QUESTIONS) == 30
    assert sum(int(q["marks"]) for q in QUESTIONS) == TOTAL_RUBRIC_POINTS
    assert "Atlas Engineering" in CASE_FACTS
    assert "No Buy/Sell/Hold recommendation" in CASE_FACTS


def test_atlas_bank_never_imported_by_matchers():
    root = Path(__file__).resolve().parents[1]
    forbidden = (
        "project_atlas_ic_case_study_held_out",
        "PROJECT ATLAS — IC RESEARCH DOSSIER",
        "Atlas Engineering Ltd.",
    )
    modules = [
        root / "institutional_reasoning" / "gold_patterns.py",
        root / "institutional_reasoning" / "family_composers.py",
        root / "institutional_reasoning" / "family_classifier.py",
        root / "institutional_reasoning" / "adversarial.py",
        root / "institutional_reasoning" / "ic_case_study.py",
        root / "institutional_reasoning" / "bias_defense.py",
    ]
    for path in modules:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not contain held-out token {token!r}"


def test_ic_case_modes_detect_general_intents():
    assert detect_ic_case_mode("Give an executive assessment for this institutional case.")["mode"] == "ic_executive_assessment"
    assert detect_ic_case_mode("Why is Free Cash Flow negative despite higher revenue? Give at least six possible explanations. Rank them.")[
        "mode"
    ] == "ic_fcf_explanations"
    assert detect_ic_case_mode("Should Reuters change your assessment?")["mode"] == "ic_reuters_update"
    assert detect_ic_case_mode("Argue the Bear Case.")["mode"] == "ic_bear_case"


def test_executive_not_stolen_by_cash_habit():
    q = build_prompt(QUESTIONS[0])
    packaged = package_reasoning_answer(q, company="Atlas Engineering Ltd.")
    assert packaged.get("owns_executive") is True
    assert packaged.get("source") == "ic_case_study_reasoning"
    assert packaged.get("mode") == "ic_executive_assessment"
    text = (packaged.get("executive") or "").lower()
    assert "cash" in text and "roic" in text
    assert "contradict" in text


def test_project_atlas_scorecard_runs():
    report = run_project_atlas_scorecard()
    assert report["ok"] is True
    assert report["never_train"] is True
    assert report["total"] == 30
    assert report["points_possible"] == TOTAL_RUBRIC_POINTS
    # Soft gate: institutional IC case should clear a high bar on this set.
    assert report["passed"] >= 24, report
    assert report["points_earned"] >= 160, report
    # Spot-check scoring helper
    row = score_item(QUESTIONS[0], package_reasoning_answer(build_prompt(QUESTIONS[0])))
    assert "checks" in row
