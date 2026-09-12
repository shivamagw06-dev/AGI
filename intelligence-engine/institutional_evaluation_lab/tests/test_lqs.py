"""Learning Quality Score — independent of CIO and prior Phase 4–5 metrics."""

from __future__ import annotations

from institutional_evaluation_lab.judges.learning_quality import aggregate_lqs, judge_learning_quality
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_lqs_not_in_dimension_weights() -> None:
    assert "learning_quality" not in DIMENSION_WEIGHTS


def test_lqs_na_when_missing() -> None:
    j = judge_learning_quality({"question": "x"}, {})
    assert j["n_a"] is True


def test_lqs_scores_good_learning() -> None:
    learning = {
        "learning_id": "IL-1",
        "thesis_id": "TH-1",
        "decision_id": "DEC-1",
        "portfolio_id": "PI-1",
        "outcome": "Incorrect",
        "expected": "Expected base case with margin expansion",
        "actual": "Observed pricing pressure and guidance stress",
        "difference": "Difference: underweighted pricing pressure",
        "root_cause": "Management",
        "lesson": (
            "The thesis relied too heavily on operating-margin expansion "
            "while underweighting pricing pressure."
        ),
        "future_guidance": (
            "Future IT theses should increase weighting for pricing pressure during "
            "weak global discretionary demand."
        ),
        "confidence_change": {"prior": 90, "current": 75, "delta": -15},
        "linked_monitoring_events": ["ME-1"],
        "linked_evidence": ["EV-1"],
        "learning_version": "1.0",
        "category": "Monitoring",
        "explanation": "Process lesson captured",
        "questions_answered": {"what_happened": "pricing pressure"},
        "mutates_thesis": False,
    }
    j = judge_learning_quality(
        {"question": "Infosys learning?"},
        {
            "learning_office": {
                "learning": learning,
                "deterministic": True,
                "process_memory": True,
                "knowledge_factory_updated": False,
                "mutates_thesis": False,
            }
        },
    )
    assert j["lqs"] is not None and j["lqs"] >= 70.0
    assert j["independent_of_mqs"] is True


def test_lqs_penalizes_knowledge_factory_update() -> None:
    j = judge_learning_quality(
        {"question": "x"},
        {
            "learning_office": {
                "knowledge_factory_updated": True,
                "process_memory": True,
                "learning": {
                    "learning_id": "IL-X",
                    "root_cause": "Evidence",
                    "lesson": "short",
                    "future_guidance": "should do better",
                },
            }
        },
    )
    assert float(j["components"]["replay_consistency"]["score"]) == 0.0


def test_lqs_does_not_change_overall() -> None:
    judgments = [
        {"dimension": d, "score": 80.0, "passed": True}
        for d in (
            "intent",
            "framework",
            "playbook",
            "evidence",
            "memory",
            "confidence",
            "replay",
            "unsupported_claims",
            "hallucinated_evidence",
        )
    ]
    judgments.append(
        {"dimension": "learning_quality", "lqs": 10.0, "score": 10.0, "passed": False, "independent_of_cio": True}
    )
    row = score_question({"question_id": "q1", "question": "Why?"}, judgments)
    assert row["overall"] == 80.0
    assert row["lqs"] == 10.0


def test_aggregate_lqs() -> None:
    rows = [
        {"dimensions": {"learning_quality": {"lqs": 90.0}}},
        {"dimensions": {"learning_quality": {"lqs": 70.0}}},
        {"dimensions": {"learning_quality": {"n_a": True}}},
    ]
    agg = aggregate_lqs(rows)
    assert agg["n"] == 2
    assert agg["mean_lqs"] == 80.0
