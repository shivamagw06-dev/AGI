"""AGI IDO — Institutional Decision Office acceptance tests."""

from __future__ import annotations

from institutional_decision_office import IDO_VERSION, apply_decision_office, list_api, status
from institutional_decision_office.engine import deliberate_decision
from institutional_decision_office.schema import FORBIDDEN_DECISIONS


def _thesis(**extra: object) -> dict:
    t = {
        "thesis_id": "TH-INFY-TEST",
        "company": "Infosys",
        "ticker": "INFY",
        "investment_view": "Quality compounder with durable ROE",
        "decision_status": "Watch",
        "lifecycle": "Active",
        "version": "1.0",
        "confidence": 87,
        "confidence_reason": "Confidence: 87/100 (High)",
        "confidence_change": 0.0,
        "preferred_case": "base",
        "what_market_missing": "No critical gaps",
        "monitoring_checklist": ["Track management guidance updates"],
        "ite_version": "institutional-investment-thesis-v1.0.0",
    }
    t.update(extra)
    return t


def _packs(thesis: dict, *, n_cases: int = 2, outcome: str = "deliberated") -> tuple:
    icr = {
        "icr_version": "institutional-committee-reasoning-v1.0.0",
        "n_cases": n_cases,
        "preferred_case": thesis.get("preferred_case"),
        "report": {"outcome": outcome},
    }
    icc = {
        "icc_version": "institutional-confidence-calibration-v1.0.0",
        "overall_confidence": thesis.get("confidence"),
        "report": {
            "overall_confidence": thesis.get("confidence"),
            "confidence_reason": thesis.get("confidence_reason"),
        },
    }
    return {"thesis": thesis}, icr, icc


def test_ido_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["release"] == "AGI v4.0"
    assert IDO_VERSION.startswith("institutional-decision-office")
    assert s["orders"] is False
    assert s["buy_sell"] is False
    assert s["freeze_locks"]["analysis_separate_from_decision"] is True


def test_deterministic_and_no_orders() -> None:
    thesis, icr, icc = _packs(_thesis(confidence=88, preferred_case="base"))
    a = deliberate_decision(
        question="Infosys office decision?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    b = deliberate_decision(
        question="Infosys office decision?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    assert a["decision"]["decision"] == b["decision"]["decision"]
    assert a["orders_emitted"] is False
    assert a["buy_sell_emitted"] is False
    assert a["decision"]["buy_sell"] is None
    assert a["decision"]["decision"] not in FORBIDDEN_DECISIONS
    assert a["decision"]["analysis_decision_separated"] is True


def test_positive_analysis_can_still_wait() -> None:
    # Bear preferred + moderate confidence → Wait (analysis may still exist)
    thesis, icr, icc = _packs(
        _thesis(confidence=70, preferred_case="bear", investment_view="Still interesting long-term")
    )
    pack = deliberate_decision(
        question="Infosys?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    assert pack["decision"]["decision"] == "Wait"
    assert "not imply action" in pack["decision"]["reason"].lower() or "Wait" in pack["decision"]["reason"]


def test_earnings_review_decision() -> None:
    thesis, icr, icc = _packs(
        _thesis(
            confidence=72,
            preferred_case="base",
            monitoring_checklist=["Await next earnings release before formal review"],
            what_market_missing="Await earnings",
        )
    )
    pack = deliberate_decision(
        question="Infosys?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    assert pack["decision"]["decision"] == "Review After Earnings"
    assert "earnings" in pack["decision"]["review_trigger"].lower()


def test_confidence_drop_escalates() -> None:
    thesis, icr, icc = _packs(_thesis(confidence=70, preferred_case="base", confidence_change=-12.0))
    pack = deliberate_decision(
        question="Infosys?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    assert pack["decision"]["decision"] == "Escalate"


def test_insufficient_rejects() -> None:
    thesis, icr, icc = _packs(_thesis(confidence=20), n_cases=0, outcome="insufficient_evidence")
    pack = deliberate_decision(
        question="Unknown?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    assert pack["decision"]["decision"] == "Reject"


def test_approve_is_process_not_trade() -> None:
    thesis, icr, icc = _packs(
        _thesis(
            confidence=85,
            preferred_case="base",
            confidence_change=0.0,
            monitoring_checklist=["Track franchise metrics"],
            what_market_missing="No critical missing-evidence items flagged",
        )
    )
    pack = deliberate_decision(
        question="Infosys?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
        persist=True,
    )
    assert pack["decision"]["decision"] == "Approve"
    assert pack["decision"]["execution"] is False
    assert "not an order" in pack["decision"]["reason"].lower()


def test_list_query_and_flags() -> None:
    thesis, icr, icc = _packs(
        _thesis(
            thesis_id="TH-INFY-EARN",
            confidence=70,
            preferred_case="base",
            monitoring_checklist=["Await next earnings release before formal review"],
        )
    )
    apply_decision_office(
        question="Infosys earnings path?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
    )
    rows = list_api({"review_trigger": "earnings", "limit": 20})
    assert rows["n"] >= 1
    out = apply_decision_office(
        question="Infosys earnings path?",
        investment_thesis=thesis,
        committee_reasoning=icr,
        confidence_calibration=icc,
    )
    assert out["pack"]["judgment_changed"] is False
    assert out["pack"]["thesis_changed"] is False
