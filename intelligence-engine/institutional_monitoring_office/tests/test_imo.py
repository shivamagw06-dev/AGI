"""AGI IMO — Institutional Monitoring Office acceptance tests."""

from __future__ import annotations

from institutional_monitoring_office import IMO_VERSION, apply_monitoring_office, status
from institutional_monitoring_office.engine import run_monitoring_office
from institutional_monitoring_office.schema import MONITOR_DOMAINS, RECOMMENDED_ACTIONS
from institutional_monitoring_office.store import reset_monitoring_store_for_tests


def setup_function() -> None:
    reset_monitoring_store_for_tests()


def _idea(**extra: object) -> dict:
    idea = {
        "idea_id": "PI-INFY-IT",
        "company": "Infosys",
        "ticker": "INFY",
        "sector": "IT Services",
        "investment_thesis_id": "TH-INFY-M",
        "decision_id": "DEC-MON-1",
        "decision": "Monitor",
        "monitoring": ["Await next earnings release", "Track guidance language"],
        "expected_role": "Core Compounder",
        "conviction": 82.0,
    }
    idea.update(extra)
    return {"idea": idea}


def _thesis(**extra: object) -> dict:
    t = {
        "thesis_id": "TH-INFY-M",
        "company": "Infosys",
        "ticker": "INFY",
        "investment_view": "Quality compounder with durable ROE",
        "version": "1.0",
        "confidence": 82,
        "preferred_case": "base",
        "monitoring_checklist": ["Await next earnings release before formal review"],
    }
    t.update(extra)
    return {"thesis": t}


def _decision(**extra: object) -> dict:
    d = {
        "decision_id": "DEC-MON-1",
        "thesis_id": "TH-INFY-M",
        "company": "Infosys",
        "ticker": "INFY",
        "decision": "Monitor",
        "status": "Monitoring",
        "confidence": 82,
    }
    d.update(extra)
    return {"decision": d}


def test_imo_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["release"] == "AGI v4.0"
    assert IMO_VERSION.startswith("institutional-monitoring-office")
    assert s["mutates_thesis"] is False
    assert s["positions"] is False
    assert s["freeze_locks"]["events_recommend_review_only"] is True
    assert len(s["domains"]) == len(MONITOR_DOMAINS)


def test_events_do_not_mutate_objects() -> None:
    pack = run_monitoring_office(
        question="What changed for Infosys after sector demand softness?",
        portfolio_office=_idea(),
        investment_thesis=_thesis(),
        decision_office=_decision(),
        confidence_calibration={"overall_confidence": 82},
        persist=True,
    )
    assert pack["n_events"] >= 1
    assert pack["mutates_thesis"] is False
    assert pack["mutates_decision"] is False
    assert pack["mutates_portfolio"] is False
    assert pack["thesis_changed"] is False
    assert pack["decision_changed"] is False
    assert pack["portfolio_changed"] is False
    assert pack["positions_emitted"] is False
    for ev in pack["events"]:
        assert ev["mutates_thesis"] is False
        assert set(ev.keys()) >= {
            "event_id",
            "portfolio_idea",
            "trigger",
            "source",
            "severity",
            "affected_thesis",
            "affected_decision",
            "affected_confidence",
            "recommended_action",
            "requires_review",
            "timestamp",
        }
        assert ev["recommended_action"] in RECOMMENDED_ACTIONS


def test_confidence_drop_recommends_review() -> None:
    run_monitoring_office(
        question="Baseline Infosys monitoring",
        portfolio_office=_idea(),
        investment_thesis=_thesis(confidence=90),
        decision_office=_decision(confidence=90),
        confidence_calibration={"overall_confidence": 90},
        persist=True,
    )
    pack = run_monitoring_office(
        question="Confidence fell after weak commentary",
        portfolio_office=_idea(),
        investment_thesis=_thesis(confidence=75),
        decision_office=_decision(confidence=75),
        confidence_calibration={"overall_confidence": 75},
        persist=True,
    )
    codes = [e["trigger"]["code"] for e in pack["events"]]
    assert "confidence_drop_gt_10" in codes
    drop = next(e for e in pack["events"] if e["trigger"]["code"] == "confidence_drop_gt_10")
    assert drop["recommended_action"] == "Review"
    assert drop["requires_review"] is True


def test_guidance_withdrawn_escalates() -> None:
    pack = run_monitoring_office(
        question="Infosys withdrew guidance for FY27 — what changed?",
        portfolio_office=_idea(),
        investment_thesis=_thesis(),
        decision_office=_decision(),
        persist=True,
    )
    ev = next(e for e in pack["events"] if e["trigger"]["code"] == "guidance_withdrawn")
    assert ev["recommended_action"] == "Escalate"
    assert ev["severity"] == "critical"


def test_results_published_refresh_thesis() -> None:
    pack = run_monitoring_office(
        question="Infosys quarterly results published — refresh needed?",
        portfolio_office=_idea(),
        investment_thesis=_thesis(),
        decision_office=_decision(),
        persist=True,
    )
    ev = next(e for e in pack["events"] if e["trigger"]["code"] == "quarterly_results_published")
    assert ev["recommended_action"] == "Refresh Thesis"


def test_bull_invalidated_committee_review() -> None:
    pack = run_monitoring_office(
        question="Has the bull case been invalidated for Infosys?",
        portfolio_office=_idea(),
        investment_thesis=_thesis(),
        decision_office=_decision(),
        hypothesis_evaluation={"invalidated": ["bull growth acceleration"]},
        persist=True,
    )
    ev = next(e for e in pack["events"] if e["trigger"]["code"] == "bull_case_invalidated")
    assert ev["recommended_action"] == "Committee Review"


def test_apply_monitoring_office_facade() -> None:
    out = apply_monitoring_office(
        question="Sector development in IT services for Infosys peers",
        portfolio_office=_idea(),
        investment_thesis=_thesis(),
        decision_office=_decision(),
        persist=True,
    )
    pack = out["pack"]
    assert pack["imo_version"].startswith("institutional-monitoring-office")
    assert pack["domains_covered"] == list(MONITOR_DOMAINS)
    assert out["report"]["mutates_thesis"] is False
