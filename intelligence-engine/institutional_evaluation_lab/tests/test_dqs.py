"""Decision Quality Score — independent of CIO / ITQS / other Phase 4–5 metrics."""

from __future__ import annotations

from institutional_evaluation_lab.judges.decision_quality import aggregate_dqs, judge_decision_quality
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_dqs_not_in_dimension_weights() -> None:
    assert "decision_quality" not in DIMENSION_WEIGHTS


def test_dqs_na_when_missing() -> None:
    j = judge_decision_quality({"question": "x"}, {})
    assert j["n_a"] is True
    assert j["independent_of_cio"] is True


def test_dqs_scores_good_decision() -> None:
    d = {
        "decision_id": "DEC-1",
        "thesis_id": "TH-1",
        "decision": "Wait",
        "reason": "Decision: Wait — positive analysis does not imply action.",
        "required_conditions": ["Clearer separation"],
        "dependencies": ["thesis:TH-1"],
        "confidence": 70,
        "owner": "AGI Investment Office",
        "review_date": "2026-08-28",
        "review_trigger": "Thesis update",
        "status": "Watch",
        "version": "1.0",
        "analysis_decision_separated": True,
        "provenance": {"ite_version": "x"},
        "buy_sell": None,
        "execution": False,
        "judgment_stack_modified": False,
        "thesis_modified": False,
    }
    j = judge_decision_quality(
        {"question": "Infosys?"},
        {
            "decision_office": {"decision": d, "buy_sell_emitted": False, "orders_emitted": False},
            "investment_thesis": {"thesis": {"investment_view": "Quality compounder"}},
        },
    )
    assert j["dqs"] is not None and j["dqs"] >= 70.0


def test_dqs_penalizes_buy_sell() -> None:
    j = judge_decision_quality(
        {"question": "x"},
        {
            "decision_office": {
                "buy_sell_emitted": True,
                "decision": {
                    "decision": "BUY",
                    "buy_sell": "BUY",
                    "reason": "buy",
                    "status": "Approved",
                    "analysis_decision_separated": False,
                },
            }
        },
    )
    assert float(j["components"]["decision_consistency"]["score"]) == 0.0


def test_dqs_does_not_change_overall() -> None:
    judgments = [
        {"dimension": dim, "score": 80.0, "passed": True}
        for dim in (
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
        {"dimension": "decision_quality", "dqs": 10.0, "score": 10.0, "passed": False, "independent_of_cio": True}
    )
    row = score_question({"question_id": "q1", "question": "Why?"}, judgments)
    assert row["overall"] == 80.0
    assert row["dqs"] == 10.0


def test_aggregate_dqs() -> None:
    rows = [
        {"dimensions": {"decision_quality": {"dqs": 90.0}}},
        {"dimensions": {"decision_quality": {"dqs": 70.0}}},
        {"dimensions": {"decision_quality": {"n_a": True}}},
    ]
    agg = aggregate_dqs(rows)
    assert agg["n"] == 2
    assert agg["mean_dqs"] == 80.0
