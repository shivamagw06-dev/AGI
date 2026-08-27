"""AGI ITE — Institutional Investment Thesis Engine acceptance tests."""

from __future__ import annotations

from institutional_investment_thesis import ITE_VERSION, apply_investment_thesis, list_api, status
from institutional_investment_thesis import store as thesis_store
from institutional_investment_thesis.engine import construct_thesis
from institutional_investment_thesis.schema import FORBIDDEN_DECISIONS


def _judgment_packs(*, confidence: int = 87, company_q: str = "Should I study Infosys as an investment?"):
    iew = {
        "iew_version": "institutional-evidence-weighting-v1.0.0",
        "n_eligible": 6,
        "top_weighted": [{"evidence_id": "E1", "weight_score": 22.0}],
        "ordered_evidence": [{"evidence_id": "E1", "weight_score": 22.0}],
        "conflicts": [{"a": "E1", "b": "E2", "resolved": False}],
    }
    ihe = {
        "ihe_version": "institutional-hypothesis-evaluation-v1.0.0",
        "outcome": "preferred",
        "evaluated_hypotheses": [
            {
                "hypothesis_id": "H1",
                "hypothesis": "Quality compounder with durable ROE and cash generation",
                "status": "Preferred",
                "preferred": True,
                "evaluation_score": 78,
                "supporting_evidence": ["E1"],
                "contradicting_evidence": ["E2"],
                "missing_evidence": [{"item": "Management guidance on margin outlook", "severity": "high"}],
            }
        ],
    }
    icr = {
        "icr_version": "institutional-committee-reasoning-v1.0.0",
        "committee_version": "icr-committee-profile-v1.0.0",
        "n_cases": 3,
        "preferred_case": "base",
        "probability_distribution": {"bull": 25.0, "base": 55.0, "bear": 20.0},
        "cases": {
            "bull": {
                "case_name": "Bull — re-rating",
                "case_type": "bull",
                "hypothesis": "Premium franchise re-rates on sustained growth",
                "hypothesis_id": "H_BULL",
                "probability_pct": 25.0,
                "confidence": 0.55,
                "supporting_evidence": ["E4"],
                "contradictory_evidence": [],
                "underlying_assumptions": ["Demand stays firm"],
                "key_catalysts": ["Large deal wins"],
                "key_risks": ["Valuation already rich"],
                "invalidation_conditions": ["Growth decelerates two quarters"],
                "missing_evidence": [],
            },
            "base": {
                "case_name": "Base — quality compounder",
                "case_type": "base",
                "hypothesis": "Quality compounder with durable ROE and cash generation",
                "hypothesis_id": "H1",
                "probability_pct": 55.0,
                "confidence": 0.7,
                "supporting_evidence": ["E1"],
                "contradictory_evidence": ["E2"],
                "underlying_assumptions": ["ROE remains elevated"],
                "key_catalysts": ["Next earnings release"],
                "key_risks": ["Wage inflation"],
                "invalidation_conditions": ["ROE compresses below peer median"],
                "missing_evidence": [{"item": "Management guidance on margin outlook"}],
            },
            "bear": {
                "case_name": "Bear — valuation air-pocket",
                "case_type": "bear",
                "hypothesis": "Valuation leaves little room for disappointment",
                "hypothesis_id": "H_BEAR",
                "probability_pct": 20.0,
                "confidence": 0.5,
                "supporting_evidence": ["E2"],
                "contradictory_evidence": ["E1"],
                "underlying_assumptions": ["Multiples mean-revert"],
                "key_catalysts": ["Guidance cut"],
                "key_risks": ["Multiple compression"],
                "invalidation_conditions": ["Sustained beat-and-raise cycle"],
                "missing_evidence": [],
            },
        },
        "report": {
            "outcome": "deliberated",
            "preferred_case": "base",
            "missing_evidence": [{"item": "Management guidance on margin outlook", "severity": "high"}],
            "citations": [{"evidence_id": "E1"}],
            "probability_distribution": {"bull": 25.0, "base": 55.0, "bear": 20.0},
        },
    }
    icc = {
        "icc_version": "institutional-confidence-calibration-v1.0.0",
        "confidence_version": "icc-confidence-profile-v1.0.0",
        "overall_confidence": confidence,
        "confidence_level": "High",
        "confidence_reason": (
            f"Confidence: {confidence}/100 (High) because evidence quality is high, "
            "committee convergence is strong, but management guidance is missing."
        ),
        "report": {
            "overall_confidence": confidence,
            "confidence_level": "High",
            "confidence_reason": (
                f"Confidence: {confidence}/100 (High) because evidence quality is high, "
                "committee convergence is strong, but management guidance is missing."
            ),
        },
    }
    return company_q, iew, ihe, icr, icc


def test_ite_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["release"] == "AGI v4.0"
    assert ITE_VERSION.startswith("institutional-investment-thesis")
    assert s["freeze_locks"]["judgment_stack_v36"] is True
    assert s["freeze_locks"]["no_buy_sell_in_ite"] is True
    assert s["buy_sell"] is False


def test_deterministic_persistent_thesis() -> None:
    q, iew, ihe, icr, icc = _judgment_packs()
    a = construct_thesis(
        question=q,
        ticker="INFY",
        company="Infosys",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    b = construct_thesis(
        question=q,
        ticker="INFY",
        company="Infosys",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    assert a["thesis_id"] == b["thesis_id"]
    t = a["thesis"]
    assert t["company"] == "Infosys"
    assert t["decision_status"] == "Watch"
    assert t["buy_sell"] is None
    assert t["analysis_only"] is True
    assert t["confidence"] == 87
    assert t["bull_case"] and t["base_case"] and t["bear_case"]
    assert t["monitoring_checklist"]
    assert t["version"] in {"1.0", "1.1", "1.2", "1.3"}
    # Retrievable after construction
    got = thesis_store.get(a["thesis_id"])
    assert got is not None
    assert got["thesis_id"] == a["thesis_id"]


def test_no_buy_sell_emitted() -> None:
    q, iew, ihe, icr, icc = _judgment_packs()
    pack = construct_thesis(
        question=q,
        company="Infosys",
        ticker="INFY",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    t = pack["thesis"]
    assert pack["buy_sell_emitted"] is False
    assert t["decision_status"] not in FORBIDDEN_DECISIONS
    assert t["decision_status"] == "Watch"


def test_ten_questions_present() -> None:
    q, iew, ihe, icr, icc = _judgment_packs()
    t = construct_thesis(
        question=q,
        company="Infosys",
        ticker="INFY",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )["thesis"]
    assert len(t["ten_questions"]) == 10
    assert t["investment_view"]
    assert t["why_now"]
    assert t["what_market_missing"]
    assert t["catalysts"]
    assert t["risks"]
    assert t["invalidation"]
    assert t["monitoring_checklist"]


def test_versioning_on_update() -> None:
    q, iew, ihe, icr, icc = _judgment_packs(confidence=90)
    first = construct_thesis(
        question=q,
        company="Infosys",
        ticker="INFY",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    v1 = first["thesis"]["version"]
    _, _, _, _, icc2 = _judgment_packs(confidence=75)
    second = construct_thesis(
        question=q,
        company="Infosys",
        ticker="INFY",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc2,
        persist=True,
    )
    assert second["thesis"]["version"] != v1
    assert float(second["thesis"].get("confidence_change") or 0) <= -10.0
    vers = thesis_store.versions(first["thesis_id"])
    assert len(vers) >= 1


def test_query_confidence_drop_and_earnings_wait() -> None:
    # Ensure a thesis with drop exists from prior test or create fresh key
    q = "Evaluate Infosys quality compounder thesis for the office"
    _, iew, ihe, icr, icc = _judgment_packs(confidence=88, company_q=q)
    construct_thesis(
        question=q,
        company="Infosys",
        ticker="INFY",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    _, _, _, _, icc2 = _judgment_packs(confidence=70, company_q=q)
    construct_thesis(
        question=q,
        company="Infosys",
        ticker="INFY",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc2,
        persist=True,
    )
    dropped = list_api({"confidence_drop_gt": 10.0, "limit": 50})
    assert dropped["n"] >= 1
    waiting = list_api({"waiting_for": "earnings", "limit": 50})
    assert waiting["n"] >= 1


def test_judgment_unchanged_flags() -> None:
    q, iew, ihe, icr, icc = _judgment_packs()
    out = apply_investment_thesis(
        question=q,
        company="Infosys",
        ticker="INFY",
        evidence_weighting=iew,
        hypothesis_evaluation=ihe,
        committee_reasoning=icr,
        confidence_calibration=icc,
    )
    pack = out["pack"]
    assert pack["reasoning_changed"] is False
    assert pack["judgment_changed"] is False
    assert pack["thesis"]["judgment_stack_modified"] is False
