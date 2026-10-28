"""Confidence Quality Score — independent of CIO / HQS / CQS / DIMENSION_WEIGHTS."""

from __future__ import annotations

from institutional_evaluation_lab.judges.confidence_quality import (
    aggregate_cfqs,
    judge_confidence_quality,
)
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_cfqs_not_in_dimension_weights() -> None:
    assert "confidence_quality" not in DIMENSION_WEIGHTS


def test_cfqs_na_when_missing_pack() -> None:
    j = judge_confidence_quality({"question": "Why?"}, {})
    assert j["n_a"] is True
    assert j["independent_of_cio"] is True
    assert j["independent_of_hqs"] is True
    assert j["independent_of_cqs"] is True


def test_cfqs_scores_good_report() -> None:
    report = {
        "overall_confidence": 87,
        "confidence_level": "High",
        "evidence_quality": 90.0,
        "coverage_score": 80.0,
        "hypothesis_strength": 78.0,
        "hypothesis_separation": 80.0,
        "conflict_score": 85.0,
        "committee_agreement": 88.0,
        "historical_score": 75.0,
        "framework_consistency": 82.0,
        "missing_evidence_penalty": 10.0,
        "temporal_integrity": True,
        "replay_integrity": True,
        "confidence_reason": (
            "Confidence: 87/100 (High) because evidence quality is high; "
            "committee agreement is strong. Confidence reduced by missing evidence penalty −10. "
            "Additional evidence that would raise confidence: Management guidance."
        ),
        "confidence_version": "icc-confidence-profile-v1.0.0",
        "why_increased": ["evidence quality (90/100)"],
        "why_decreased": ["missing evidence penalty −10"],
        "missing_evidence_that_would_raise": ["Management guidance"],
        "unresolved_conflicting_evidence": [],
        "evidence_reducing_confidence": [],
        "penalties": {"missing_evidence": 10.0, "fixture_dependence": 0.0, "total": 10.0},
        "llm_used": False,
        "manually_assigned": False,
        "fixture_raised_confidence": False,
        "deterministic": True,
    }
    j = judge_confidence_quality(
        {"question": "Why did margins decline?"},
        {
            "confidence_calibration": {
                "report": report,
                "overall_confidence": 87,
                "deterministic": True,
                "llm_used": False,
                "manually_assigned": False,
            }
        },
    )
    assert j["cfqs"] is not None and j["cfqs"] >= 70.0
    assert j["independent_of_cqs"] is True


def test_cfqs_penalizes_manual_or_llm() -> None:
    j = judge_confidence_quality(
        {"question": "Why?"},
        {
            "confidence_calibration": {
                "llm_used": True,
                "deterministic": False,
                "report": {
                    "overall_confidence": 90,
                    "confidence_level": "Very High",
                    "evidence_quality": 90,
                    "coverage_score": 90,
                    "hypothesis_strength": 90,
                    "hypothesis_separation": 90,
                    "conflict_score": 90,
                    "committee_agreement": 90,
                    "historical_score": 90,
                    "framework_consistency": 90,
                    "missing_evidence_penalty": 0,
                    "temporal_integrity": True,
                    "replay_integrity": True,
                    "confidence_reason": "Confidence: 90/100 (Very High)",
                    "confidence_version": "x",
                    "llm_used": True,
                    "manually_assigned": False,
                },
            }
        },
    )
    assert float(j["components"]["determinism"]["score"]) < 50.0
    assert float(j["components"]["calibration"]["score"]) == 0.0


def test_cfqs_does_not_change_overall_score() -> None:
    judgments = [
        {"dimension": "intent", "score": 80.0, "passed": True},
        {"dimension": "framework", "score": 80.0, "passed": True},
        {"dimension": "playbook", "score": 80.0, "passed": True},
        {"dimension": "evidence", "score": 80.0, "passed": True},
        {"dimension": "memory", "score": 80.0, "passed": True},
        {"dimension": "confidence", "score": 80.0, "passed": True},
        {"dimension": "replay", "score": 80.0, "passed": True},
        {"dimension": "unsupported_claims", "score": 80.0, "passed": True},
        {"dimension": "hallucinated_evidence", "score": 80.0, "passed": True},
        {
            "dimension": "confidence_quality",
            "cfqs": 10.0,
            "score": 10.0,
            "passed": False,
            "root_cause": "cfqs_weak_explainability",
            "independent_of_cio": True,
        },
    ]
    row = score_question({"question_id": "q1", "question": "Why?"}, judgments)
    assert row["overall"] == 80.0
    assert row["cfqs"] == 10.0
    assert "confidence_quality" in row["dimensions"]


def test_aggregate_cfqs() -> None:
    rows = [
        {"dimensions": {"confidence_quality": {"cfqs": 90.0, "passed": True}}},
        {"dimensions": {"confidence_quality": {"cfqs": 70.0, "passed": True}}},
        {"dimensions": {"confidence_quality": {"n_a": True}}},
    ]
    agg = aggregate_cfqs(rows)
    assert agg["n"] == 2
    assert agg["mean_cfqs"] == 80.0
    assert agg["independent_of_cio"] is True
