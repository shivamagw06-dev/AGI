"""Portfolio Quality Score — independent of CIO and prior Phase 4–5 metrics."""

from __future__ import annotations

from institutional_evaluation_lab.judges.portfolio_quality import aggregate_pqs, judge_portfolio_quality
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_pqs_not_in_dimension_weights() -> None:
    assert "portfolio_quality" not in DIMENSION_WEIGHTS


def test_pqs_na_when_missing() -> None:
    j = judge_portfolio_quality({"question": "x"}, {})
    assert j["n_a"] is True


def test_pqs_scores_good_idea() -> None:
    idea = {
        "idea_id": "PI-1",
        "company": "Infosys",
        "ticker": "INFY",
        "sector": "IT Services",
        "theme": "India IT compounders",
        "investment_thesis_id": "TH-1",
        "decision_id": "DEC-1",
        "decision": "Wait",
        "relative_rank": 2,
        "conviction": 78.0,
        "expected_role": "Core Compounder",
        "correlation": "High peer correlation",
        "risk_budget": "Unallocated",
        "capacity": "Idea capacity only",
        "monitoring": ["Await earnings"],
        "investment_view": "Quality compounder",
        "position": None,
        "constraint_check": {
            "compliant": True,
            "violations": [],
            "policies": {"allow_positions": False, "allow_execution": False},
        },
        "peer_ranking": [{"rank": 1, "ticker": "TCS"}, {"rank": 2, "ticker": "INFY"}],
    }
    j = judge_portfolio_quality(
        {"question": "Infosys vs IT?"},
        {
            "portfolio_office": {
                "idea": idea,
                "peer_ranking": idea["peer_ranking"],
                "positions_emitted": False,
                "orders_emitted": False,
            },
            "decision_office": {"decision": {"decision": "Wait", "decision_id": "DEC-1"}},
        },
    )
    assert j["pqs"] is not None and j["pqs"] >= 70.0


def test_pqs_penalizes_positions() -> None:
    j = judge_portfolio_quality(
        {"question": "x"},
        {
            "portfolio_office": {
                "positions_emitted": True,
                "idea": {
                    "idea_id": "PI-X",
                    "expected_role": "Satellite",
                    "position": {"qty": 100},
                    "position_size": 0.05,
                },
            }
        },
    )
    assert float(j["components"]["constraint_compliance"]["score"]) == 0.0


def test_pqs_does_not_change_overall() -> None:
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
        {"dimension": "portfolio_quality", "pqs": 10.0, "score": 10.0, "passed": False, "independent_of_cio": True}
    )
    row = score_question({"question_id": "q1", "question": "Why?"}, judgments)
    assert row["overall"] == 80.0
    assert row["pqs"] == 10.0


def test_aggregate_pqs() -> None:
    rows = [
        {"dimensions": {"portfolio_quality": {"pqs": 90.0}}},
        {"dimensions": {"portfolio_quality": {"pqs": 70.0}}},
        {"dimensions": {"portfolio_quality": {"n_a": True}}},
    ]
    agg = aggregate_pqs(rows)
    assert agg["n"] == 2
    assert agg["mean_pqs"] == 80.0
