"""Investment Thesis Quality Score — independent of CIO / HQS / CQS / CFQS."""

from __future__ import annotations

from institutional_evaluation_lab.judges.thesis_quality import aggregate_itqs, judge_thesis_quality
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_itqs_not_in_dimension_weights() -> None:
    assert "thesis_quality" not in DIMENSION_WEIGHTS


def test_itqs_na_when_missing() -> None:
    j = judge_thesis_quality({"question": "x"}, {})
    assert j["n_a"] is True
    assert j["independent_of_cio"] is True


def test_itqs_scores_good_thesis() -> None:
    thesis = {
        "thesis_id": "TH-INFY-1",
        "company": "Infosys",
        "investment_view": "Quality compounder",
        "why_now": "Why now: evidence available",
        "what_market_missing": "Guidance missing",
        "bull_case": {"hypothesis": "upside"},
        "base_case": {"hypothesis": "base"},
        "bear_case": {"hypothesis": "downside"},
        "supporting_evidence": [{"evidence_id": "E1"}],
        "counter_evidence": ["E2"],
        "catalysts": ["Next earnings release"],
        "risks": ["Wage inflation"],
        "invalidation": ["ROE compresses"],
        "monitoring_checklist": ["Await next earnings release before formal review"],
        "decision_status": "Watch",
        "lifecycle": "Active",
        "confidence": 87,
        "confidence_reason": "Confidence: 87/100 (High) because evidence quality is high",
        "version": "1.0",
        "owner": "AGI Investment Office",
        "citations": [{"evidence_id": "E1"}],
        "ten_questions": [{"id": "investment_view"}],
        "last_updated": "2026-07-28T00:00:00Z",
        "created_at": "2026-07-28T00:00:00Z",
        "buy_sell": None,
        "analysis_only": True,
        "judgment_stack_modified": False,
    }
    j = judge_thesis_quality(
        {"question": "Infosys?"},
        {"investment_thesis": {"thesis": thesis}},
    )
    assert j["itqs"] is not None and j["itqs"] >= 70.0


def test_itqs_penalizes_buy_sell() -> None:
    j = judge_thesis_quality(
        {"question": "x"},
        {
            "investment_thesis": {
                "thesis": {
                    "thesis_id": "T1",
                    "company": "X",
                    "investment_view": "v",
                    "why_now": "n",
                    "what_market_missing": "m",
                    "decision_status": "BUY",
                    "lifecycle": "Active",
                    "confidence": 90,
                    "confidence_reason": "Confidence: 90/100",
                    "version": "1.0",
                    "owner": "AGI",
                    "monitoring_checklist": ["earnings"],
                    "buy_sell": "BUY",
                    "analysis_only": False,
                }
            }
        },
    )
    assert float(j["components"]["internal_consistency"]["score"]) == 0.0


def test_itqs_does_not_change_overall() -> None:
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
        {
            "dimension": "thesis_quality",
            "itqs": 10.0,
            "score": 10.0,
            "passed": False,
            "independent_of_cio": True,
        }
    )
    row = score_question({"question_id": "q1", "question": "Why?"}, judgments)
    assert row["overall"] == 80.0
    assert row["itqs"] == 10.0


def test_aggregate_itqs() -> None:
    rows = [
        {"dimensions": {"thesis_quality": {"itqs": 90.0}}},
        {"dimensions": {"thesis_quality": {"itqs": 70.0}}},
        {"dimensions": {"thesis_quality": {"n_a": True}}},
    ]
    agg = aggregate_itqs(rows)
    assert agg["n"] == 2
    assert agg["mean_itqs"] == 80.0
