"""Monitoring Quality Score — independent of CIO and prior Phase 4–5 metrics."""

from __future__ import annotations

from institutional_evaluation_lab.judges.monitoring_quality import aggregate_mqs, judge_monitoring_quality
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_mqs_not_in_dimension_weights() -> None:
    assert "monitoring_quality" not in DIMENSION_WEIGHTS


def test_mqs_na_when_missing() -> None:
    j = judge_monitoring_quality({"question": "x"}, {})
    assert j["n_a"] is True


def test_mqs_scores_good_pack() -> None:
    events = [
        {
            "event_id": "ME-1",
            "portfolio_idea": "PI-1",
            "trigger": {
                "code": "confidence_drop_gt_10",
                "domain": "Confidence",
                "description": "Confidence dropped 12 points",
            },
            "source": "confidence_calibration",
            "severity": "medium",
            "affected_thesis": "TH-1",
            "affected_decision": "DEC-1",
            "affected_confidence": {"prior": 90, "current": 75, "delta": -15},
            "recommended_action": "Review",
            "requires_review": True,
            "timestamp": "2026-07-28T12:00:00Z",
            "explanation": "Confidence dropped",
            "mutates_thesis": False,
        },
        {
            "event_id": "ME-2",
            "portfolio_idea": "PI-1",
            "trigger": {
                "code": "coverage_heartbeat",
                "domain": "Sector",
                "description": "Coverage across 10 domains",
            },
            "source": "institutional_monitoring_office",
            "severity": "info",
            "affected_thesis": "TH-1",
            "affected_decision": "DEC-1",
            "affected_confidence": {"current": 75},
            "recommended_action": "Monitor",
            "requires_review": False,
            "timestamp": "2026-07-28T12:00:00Z",
            "explanation": "Heartbeat",
            "mutates_thesis": False,
            "domains_covered": [
                "Earnings",
                "Guidance",
                "Management Commentary",
                "Corporate Actions",
                "Regulatory",
                "Macro",
                "Sector",
                "Competitor",
                "Valuation",
                "Confidence",
            ],
        },
    ]
    j = judge_monitoring_quality(
        {"question": "What changed for Infosys?"},
        {
            "monitoring_office": {
                "portfolio_idea": "PI-1",
                "events": events,
                "n_events": 2,
                "requires_review": 1,
                "domains_covered": events[1]["domains_covered"],
                "timestamp": "2026-07-28T12:00:00Z",
                "deterministic": True,
                "mutates_thesis": False,
                "mutates_decision": False,
                "mutates_portfolio": False,
            }
        },
    )
    assert j["mqs"] is not None and j["mqs"] >= 70.0
    assert j["independent_of_pqs"] is True


def test_mqs_penalizes_mutation() -> None:
    j = judge_monitoring_quality(
        {"question": "x"},
        {
            "monitoring_office": {
                "mutates_thesis": True,
                "events": [
                    {
                        "event_id": "ME-X",
                        "trigger": {"code": "x", "domain": "Sector"},
                        "recommended_action": "Review",
                        "requires_review": True,
                        "mutates_thesis": True,
                    }
                ],
                "domains_covered": ["Sector"],
            }
        },
    )
    assert float(j["components"]["false_positive_discipline"]["score"]) == 0.0


def test_mqs_does_not_change_overall() -> None:
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
        {"dimension": "monitoring_quality", "mqs": 10.0, "score": 10.0, "passed": False, "independent_of_cio": True}
    )
    row = score_question({"question_id": "q1", "question": "Why?"}, judgments)
    assert row["overall"] == 80.0
    assert row["mqs"] == 10.0


def test_aggregate_mqs() -> None:
    rows = [
        {"dimensions": {"monitoring_quality": {"mqs": 90.0}}},
        {"dimensions": {"monitoring_quality": {"mqs": 70.0}}},
        {"dimensions": {"monitoring_quality": {"n_a": True}}},
    ]
    agg = aggregate_mqs(rows)
    assert agg["n"] == 2
    assert agg["mean_mqs"] == 80.0
