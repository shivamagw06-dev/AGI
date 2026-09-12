"""Hypothesis Quality Score — independent of CIO / DIMENSION_WEIGHTS."""

from __future__ import annotations

from institutional_evaluation_lab.judges.hypothesis_quality import (
    aggregate_hqs,
    judge_hypothesis_quality,
)
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_hqs_not_in_dimension_weights() -> None:
    assert "hypothesis_quality" not in DIMENSION_WEIGHTS


def test_hqs_na_when_missing_pack() -> None:
    j = judge_hypothesis_quality({"question": "Why did margins decline?"}, {})
    assert j["n_a"] is True
    assert j["independent_of_cio"] is True
    assert j["passed"] is True


def test_hqs_scores_good_margin_pack() -> None:
    pack = {
        "n_hypotheses": 3,
        "outcome": "preferred",
        "plural": True,
        "forced_single_winner": False,
        "insufficient_evidence": False,
        "fabricated": False,
        "llm_used": False,
        "families": ["margin_decline"],
        "hypotheses": [
            {
                "hypothesis_id": "H1",
                "hypothesis": "Input-cost inflation compressed margins",
                "category": "Company",
                "template_key": "input_cost_inflation",
                "supporting_evidence": ["E1"],
                "contradicting_evidence": ["E2"],
                "overall_score": 80,
                "status": "Preferred",
                "reason": "Why preferred: strongest support",
            },
            {
                "hypothesis_id": "H2",
                "hypothesis": "Pricing pressure reduced realized prices",
                "category": "Industry",
                "template_key": "pricing_pressure",
                "supporting_evidence": ["E3"],
                "contradicting_evidence": [],
                "overall_score": 55,
                "status": "Active",
                "reason": "retained",
            },
            {
                "hypothesis_id": "H3",
                "hypothesis": "Execution issues",
                "category": "Company",
                "template_key": "execution_issues",
                "supporting_evidence": ["E4"],
                "contradicting_evidence": [],
                "overall_score": 10,
                "status": "Rejected",
                "reason": "Why rejected: weak support",
                "reject_reason": "weak",
            },
        ],
    }
    j = judge_hypothesis_quality(
        {"question": "Why did margins decline?"},
        {"hypothesis_generation": pack, "evidence_weighting": {"conflicts": [{"topic": "x"}]}},
    )
    assert j["n_a"] is False
    assert j["hqs"] is not None and j["hqs"] >= 70.0
    assert j["passed"] is True
    assert j["independent_of_cio"] is True


def test_hqs_penalizes_fabricated() -> None:
    j = judge_hypothesis_quality(
        {"question": "Why?"},
        {
            "hypothesis_generation": {
                "n_hypotheses": 2,
                "fabricated": True,
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "hypothesis": "Made up",
                        "category": "Company",
                        "supporting_evidence": [],
                        "overall_score": 90,
                        "status": "Preferred",
                    },
                    {
                        "hypothesis_id": "H2",
                        "hypothesis": "Also made up",
                        "category": "Macro",
                        "supporting_evidence": [],
                        "overall_score": 10,
                        "status": "Active",
                    },
                ],
            }
        },
    )
    assert j["passed"] is False
    assert float(j["hqs"]) < 70.0


def test_hqs_does_not_change_overall_score() -> None:
    judgments = [
        {"dimension": "intent", "passed": True, "score": 100.0},
        {"dimension": "framework", "passed": True, "score": 100.0},
        {"dimension": "playbook", "passed": True, "score": 100.0},
        {"dimension": "evidence", "passed": True, "score": 100.0},
        {"dimension": "memory", "passed": True, "score": 100.0},
        {"dimension": "confidence", "passed": True, "score": 100.0},
        {"dimension": "replay", "passed": True, "score": 100.0},
        {"dimension": "unsupported_claims", "passed": True, "score": 100.0},
        {"dimension": "hallucinated_evidence", "passed": True, "score": 100.0},
        {
            "dimension": "hypothesis_quality",
            "passed": False,
            "score": 10.0,
            "hqs": 10.0,
            "independent_of_cio": True,
            "root_cause": "hqs_weak_plausibility",
        },
    ]
    row = score_question({"question_id": "Q1", "category": "company"}, judgments)
    assert row["overall"] == 100.0
    assert row["passed"] is True
    assert row["hqs"] == 10.0
    assert "hypothesis_quality" in row["dimensions"]


def test_aggregate_hqs() -> None:
    rows = [
        {"dimensions": {"hypothesis_quality": {"hqs": 80.0, "passed": True, "outcome": "preferred"}}},
        {"dimensions": {"hypothesis_quality": {"hqs": 60.0, "passed": False, "outcome": "contested"}}},
        {"dimensions": {"hypothesis_quality": {"n_a": True}}},
    ]
    agg = aggregate_hqs(rows)
    assert agg["n_scored"] == 2
    assert agg["n_na"] == 1
    assert agg["mean_hqs"] == 70.0
    assert agg["independent_of_cio"] is True
