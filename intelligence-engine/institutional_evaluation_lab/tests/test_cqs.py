"""Committee Quality Score — independent of CIO / HQS / DIMENSION_WEIGHTS."""

from __future__ import annotations

from institutional_evaluation_lab.judges.committee_quality import (
    aggregate_cqs,
    judge_committee_quality,
)
from institutional_evaluation_lab.schema import DIMENSION_WEIGHTS
from institutional_evaluation_lab.scoring.engine import score_question


def test_cqs_not_in_dimension_weights() -> None:
    assert "committee_quality" not in DIMENSION_WEIGHTS


def test_cqs_na_when_missing_pack() -> None:
    j = judge_committee_quality({"question": "Why did margins decline?"}, {})
    assert j["n_a"] is True
    assert j["independent_of_cio"] is True
    assert j["independent_of_hqs"] is True
    assert j["passed"] is True


def _full_case(role: str, hyp: str, prob: float) -> dict:
    return {
        "case_name": f"{role.title()} — {hyp}",
        "case_type": role,
        "hypothesis_id": f"H_{role}",
        "hypothesis": hyp,
        "supporting_evidence": ["E1"],
        "contradictory_evidence": ["E2"],
        "underlying_assumptions": ["Costs stay elevated"],
        "required_conditions": ["Input costs remain high"],
        "key_catalysts": ["Next cost print"],
        "key_risks": ["Pricing recovery"],
        "invalidation_conditions": ["Gross margin expands QoQ"],
        "confidence": 0.6,
        "probability": prob,
        "probability_pct": round(100 * prob, 2),
        "evidence_coverage": 0.5,
        "historical_analogues": ["MEM1"],
        "framework_alignment": {"aligned": True},
        "missing_evidence": [{"item": "SKU-level mix", "severity": "medium"}],
    }


def test_cqs_scores_good_committee_pack() -> None:
    pack = {
        "n_cases": 3,
        "preferred_case": "base",
        "probability_distribution": {"bull": 25.0, "base": 55.0, "bear": 20.0},
        "probability_sum": 1.0,
        "voting_engine": False,
        "fabricated": False,
        "llm_used": False,
        "cases": {
            "bull": _full_case("bull", "Long-term growth optionality", 0.25),
            "base": _full_case("base", "Input-cost inflation compressed margins", 0.55),
            "bear": _full_case("bear", "Demand weakness reduced leverage", 0.20),
        },
        "report": {
            "outcome": "deliberated",
            "preferred_case": "base",
            "why_preferred": "Preferred case 'base' carries probability 55%",
            "why_alternatives_remain": "Alternatives remain plausible",
            "alternative_cases": ["bull", "bear"],
            "probability_distribution": {"bull": 25.0, "base": 55.0, "bear": 20.0},
            "key_disagreements": [{"a": "bull", "b": "bear"}],
            "major_uncertainties": ["Missing SKU mix"],
            "committee_summary": "Committee constructed 3 evidence-backed cases",
            "forced_consensus": False,
            "missing_evidence": [{"item": "SKU-level mix"}],
        },
    }
    j = judge_committee_quality(
        {"question": "Why did margins decline?"},
        {"committee_reasoning": pack},
    )
    assert j["cqs"] is not None and j["cqs"] >= 70.0
    assert j["independent_of_cio"] is True
    assert j["voting_engine"] is False


def test_cqs_penalizes_bad_probability_sum() -> None:
    j = judge_committee_quality(
        {"question": "Why?"},
        {
            "committee_reasoning": {
                "n_cases": 2,
                "preferred_case": "base",
                "probability_distribution": {"base": 60.0, "bear": 20.0},
                "voting_engine": False,
                "cases": {
                    "base": _full_case("base", "Base case", 0.6),
                    "bear": _full_case("bear", "Bear case", 0.2),
                },
                "report": {
                    "outcome": "deliberated",
                    "preferred_case": "base",
                    "why_preferred": "x",
                    "committee_summary": "y",
                    "probability_distribution": {"base": 60.0, "bear": 20.0},
                    "forced_consensus": False,
                },
            }
        },
    )
    assert float(j["components"]["probability_calibration"]["score"]) < 50.0


def test_cqs_does_not_change_overall_score() -> None:
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
            "dimension": "committee_quality",
            "cqs": 10.0,
            "score": 10.0,
            "passed": False,
            "root_cause": "cqs_weak_base_realism",
            "independent_of_cio": True,
        },
    ]
    row = score_question({"question_id": "q1", "question": "Why?"}, judgments)
    assert row["overall"] == 80.0
    assert row["cqs"] == 10.0
    assert "committee_quality" in row["dimensions"]


def test_aggregate_cqs() -> None:
    rows = [
        {"dimensions": {"committee_quality": {"cqs": 80.0, "passed": True, "outcome": "deliberated"}}},
        {"dimensions": {"committee_quality": {"cqs": 60.0, "passed": False, "outcome": "deliberated"}}},
        {"dimensions": {"committee_quality": {"n_a": True}}},
    ]
    agg = aggregate_cqs(rows)
    assert agg["n"] == 2
    assert agg["mean_cqs"] == 70.0
    assert agg["independent_of_cio"] is True
