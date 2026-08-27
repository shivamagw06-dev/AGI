"""AGI ILO — Institutional Learning Office acceptance tests."""

from __future__ import annotations

from institutional_learning_office import ILO_VERSION, apply_learning_office, status
from institutional_learning_office.engine import construct_investment_learning
from institutional_learning_office.schema import LEARNING_CATEGORIES, LEARNING_FIELDS
from institutional_learning_office.store import reset_learning_store_for_tests


def setup_function() -> None:
    reset_learning_store_for_tests()


def _thesis(**extra: object) -> dict:
    t = {
        "thesis_id": "TH-INFY-L",
        "company": "Infosys",
        "ticker": "INFY",
        "investment_view": "Quality compounder relying on operating-margin expansion",
        "version": "1.0",
        "confidence": 82,
        "preferred_case": "base",
        "lifecycle": "Active",
    }
    t.update(extra)
    return {"thesis": t}


def _decision(**extra: object) -> dict:
    d = {
        "decision_id": "DEC-L-1",
        "thesis_id": "TH-INFY-L",
        "company": "Infosys",
        "ticker": "INFY",
        "decision": "Monitor",
        "status": "Monitoring",
        "confidence": 82,
    }
    d.update(extra)
    return {"decision": d}


def _idea(**extra: object) -> dict:
    idea = {
        "idea_id": "PI-INFY-L",
        "company": "Infosys",
        "ticker": "INFY",
        "investment_thesis_id": "TH-INFY-L",
        "decision_id": "DEC-L-1",
        "expected_role": "Core Compounder",
    }
    idea.update(extra)
    return {"idea": idea}


def _monitoring(*codes: str) -> dict:
    events = []
    for i, code in enumerate(codes or ("coverage_heartbeat",)):
        events.append(
            {
                "event_id": f"ME-L-{i}",
                "portfolio_idea": "PI-INFY-L",
                "trigger": {"code": code, "domain": "Confidence", "description": code},
                "source": "test",
                "severity": "medium",
                "affected_thesis": "TH-INFY-L",
                "affected_decision": "DEC-L-1",
                "affected_confidence": {"prior": 90, "current": 75, "delta": -15},
                "recommended_action": "Review" if code != "coverage_heartbeat" else "Monitor",
                "requires_review": code != "coverage_heartbeat",
                "timestamp": "2026-07-28T12:00:00Z",
                "explanation": code,
                "mutates_thesis": False,
            }
        )
    return {"events": events, "portfolio_idea": "PI-INFY-L", "n_events": len(events)}


def test_ilo_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["release"] == "AGI v4.0"
    assert ILO_VERSION.startswith("institutional-learning-office")
    assert s["final_office_module"] is True
    assert s["no_sprint_5_6"] is True
    assert s["knowledge_factory_updated"] is False
    assert s["process_memory"] is True
    assert s["freeze_locks"]["does_not_update_knowledge_factory"] is True


def test_learning_object_fields_and_process_memory() -> None:
    pack = construct_investment_learning(
        question="Infosys faced pricing pressure after weak global discretionary demand",
        investment_thesis=_thesis(),
        decision_office=_decision(),
        portfolio_office=_idea(),
        monitoring_office=_monitoring("confidence_drop_gt_10", "guidance_withdrawn"),
        persist=True,
    )
    learning = pack["learning"]
    assert learning["learning_id"].startswith("IL-")
    for field in LEARNING_FIELDS:
        assert field in learning
    assert pack["knowledge_factory_updated"] is False
    assert pack["process_memory"] is True
    assert pack["mutates_thesis"] is False
    assert learning["category"] in LEARNING_CATEGORIES
    assert "pricing" in learning["lesson"].lower() or "process" in learning["lesson"].lower()
    assert learning["future_guidance"]


def test_closed_thesis_incorrect_path() -> None:
    pack = construct_investment_learning(
        question="Closed Infosys thesis after bull case invalidated and margin miss",
        investment_thesis=_thesis(lifecycle="Closed", preferred_case="bull"),
        decision_office=_decision(decision="Approve", status="Approved"),
        portfolio_office=_idea(),
        monitoring_office=_monitoring("bull_case_invalidated"),
        persist=True,
    )
    assert pack["learning"]["outcome"] == "Incorrect"
    assert pack["learning"]["root_cause"]


def test_does_not_update_knowledge_factory() -> None:
    out = apply_learning_office(
        question="What should AGI remember about Infosys process?",
        investment_thesis=_thesis(),
        decision_office=_decision(),
        portfolio_office=_idea(),
        monitoring_office=_monitoring("quarterly_results_published"),
        persist=True,
    )
    assert out["report"]["knowledge_factory_updated"] is False
    assert out["pack"]["freeze_locks"]["no_sprint_5_6"] is True
