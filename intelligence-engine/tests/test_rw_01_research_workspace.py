"""RW-01 — Institutional Research Workspace tests."""

from __future__ import annotations

from institutional_workspace.evidence_browser import browse_evidence, source_types
from institutional_workspace.linked_objects import build_linked_objects
from institutional_workspace.navigation import (
    ask_deep_link,
    search_workspace,
    workspace_deep_link,
    workspace_focus_for_intent,
)
from institutional_workspace.notes import add_note, reset_for_tests as reset_notes
from institutional_workspace.object_viewer import view_object
from institutional_workspace.production import (
    add_analyst_note,
    get_committee_workspace,
    get_company_workspace,
    get_object,
    get_portfolio_workspace,
    get_timeline,
    health,
    reset_for_tests,
    search,
    soft_slice_mission_control,
)
from institutional_workspace.schema import (
    COMPANY_SECTIONS,
    LINEAGE_CHAIN,
    NAVIGATION,
    PORTFOLIO_SECTIONS,
    RW_WORKSTREAM_ID,
)
from institutional_workspace.timeline import build_timeline
from institutional_workspace.workspace import (
    assemble_committee_workspace,
    assemble_company_workspace,
    assemble_portfolio_workspace,
)


def setup_function():
    reset_for_tests()
    reset_notes()


def test_health_presentation_only():
    h = health()
    assert h["workstream_id"] == RW_WORKSTREAM_ID
    assert h["generates_recommendations"] is False
    assert h["mutates_system_intelligence"] is False
    assert h["presentation_only"] is True
    assert h["notes_are_analyst_owned"] is True


def test_timeline_generation_company():
    events = build_timeline(
        context="company",
        subject_id="AXISBANK",
        company_decision={
            "decision_id": "d1",
            "recommendation": "HOLD",
            "generated_at": "2026-01-01T00:00:00Z",
        },
        portfolio_risk={"risk_id": "r1", "overall_risk": "Elevated", "generated_at": "2026-01-02T00:00:00Z"},
        policy={"policy_id": "p1", "overall_status": "Breach", "generated_at": "2026-01-03T00:00:00Z"},
        portfolio_decision={
            "decision_id": "pd1",
            "recommendation": "Reduce",
            "generated_at": "2026-01-04T00:00:00Z",
        },
        committee={
            "resolution_id": "c1",
            "status": "Approved",
            "outcome": "Reduce approved",
            "generated_at": "2026-01-05T00:00:00Z",
        },
        evidence=[{"evidence_id": "e1", "title": "Q2 Results", "date": "2026-01-01T00:00:00Z"}],
    )
    kinds = [e.kind for e in events]
    assert "evidence" in kinds
    assert "decision_updated" in kinds
    assert any("risk" in k for k in kinds)
    assert len(events) >= 4


def test_object_linking_lineage():
    links = build_linked_objects(
        ticker="HDFCBANK",
        portfolio_id="agi-core-equity",
        company_decision={"decision_id": "cd1", "recommendation": "BUY"},
        portfolio_risk={"risk_id": "rr1", "overall_risk": "Moderate"},
        policy={"policy_id": "pp1", "overall_status": "OK"},
        portfolio_decision={"decision_id": "pd1", "recommendation": "Hold"},
        committee={"resolution_id": "cr1", "status": "Pending"},
    )
    types = {o.object_type for o in links}
    assert "CompanyDecision" in types
    assert "PortfolioRisk" in types
    assert "PolicyAssessment" in types
    assert "PortfolioDecision" in types
    assert "CommitteeResolution" in types
    assert all(o.href for o in links)


def test_evidence_navigation():
    items = browse_evidence(ticker="RELIANCE", linked_decision_id="d1", linked_risk_id="r1")
    assert len(items) >= 5
    assert set(source_types()).issuperset({i.source_type for i in items} & set(source_types()))
    assert any(i.linked_object_ids for i in items)


def test_workspace_routing_company_portfolio_committee():
    company = assemble_company_workspace("AXISBANK")
    assert company.context == "company"
    assert company.ticker == "AXISBANK"
    assert company.mutates_system_intelligence is False
    for section in ("overview", "timeline", "evidence", "research_notes"):
        assert section in company.sections or section in COMPANY_SECTIONS

    portfolio = assemble_portfolio_workspace("agi-core-equity")
    assert portfolio.context == "portfolio"
    assert portfolio.portfolio_id == "agi-core-equity"
    for section in PORTFOLIO_SECTIONS[:4]:
        assert section in portfolio.sections

    committee = assemble_committee_workspace()
    assert committee.context == "committee"
    assert committee.navigation == NAVIGATION or len(committee.navigation) >= 5


def test_search_within_workspace():
    ws = assemble_company_workspace("AXISBANK")
    hits = search_workspace(ws, "risk")
    assert hits
    assert any(h["kind"] in {"timeline", "linked_object", "section", "evidence"} for h in hits)


def test_notes_never_mutate_system():
    note = add_note(
        context_key="company:TCS",
        title="Personal observation",
        body="Watch margins",
        tags=("personal",),
        linked_decision_id="d-tcs",
    )
    assert note.system_generated is False
    d = note.to_dict()
    assert d["mutates_system_intelligence"] is False
    assert d["system_generated"] is False

    result = add_analyst_note({"ticker": "TCS", "title": "Tag test", "body": "x", "tags": ["esg"]})
    assert result["ok"] is True
    assert result["mutates_system_intelligence"] is False


def test_object_viewer():
    viewed = view_object(
        "PortfolioDecision",
        {"decision_id": "pd1", "recommendation": "Reduce", "investment_posture": "Defensive"},
    )
    assert viewed["object_type"] == "PortfolioDecision"
    assert viewed["mutates_system_intelligence"] is False
    assert "Reduce" in str(viewed["summary"]) or viewed["label"]


def test_ask_workspace_deep_links():
    assert "/agi/ask" in ask_deep_link(ticker="AXISBANK", question="Why did the recommendation change?")
    href = workspace_deep_link(ticker="AXISBANK", focus="timeline")
    assert "/agi/companies/AXISBANK" in href
    assert "tab=timeline" in href
    assert workspace_focus_for_intent("Committee") == "committee"
    assert workspace_focus_for_intent("Risk") == "risk"


def test_company_workspace_integration():
    result = get_company_workspace("AXISBANK")
    assert result["ok"] is True
    assert result["presentation_only"] is True
    ws = result["workspace"]
    assert ws["context"] == "company"
    assert ws["timeline"]
    assert ws["linked_objects"]
    assert ws["evidence"]
    assert "Evidence" in LINEAGE_CHAIN


def test_portfolio_workspace_integration():
    result = get_portfolio_workspace("agi-core-equity")
    assert result["ok"] is True
    ws = result["workspace"]
    assert ws["context"] == "portfolio"
    assert "risk" in ws["sections"]
    assert "decision" in ws["sections"]


def test_committee_workspace_and_timeline_api():
    result = get_committee_workspace()
    assert result["ok"] is True
    assert result["workspace"]["context"] == "committee"

    tl = get_timeline("AXISBANK", context="company")
    assert tl["ok"] is True
    assert tl["timeline"]
    assert tl["lineage_hint"]


def test_cross_object_navigation_and_search_api():
    get_company_workspace("HDFCBANK")
    obj = get_object("soft-HDFCBANK")
    assert obj["ok"] is True
    assert "object" in obj

    hits = search("HDFCBANK", "decision", context="company")
    assert hits["ok"] is True
    assert hits["count"] >= 0


def test_mission_control_workspace_health():
    get_company_workspace("AXISBANK")
    slice_ = soft_slice_mission_control()
    assert slice_["workstream_id"] == RW_WORKSTREAM_ID
    assert slice_["workspace_health"] is True
    assert "objects_with_missing_links" in slice_
    assert "orphaned_notes" in slice_
    assert "navigation_integrity" in slice_


def test_uag_opens_workspace_context():
    from institutional_orchestrator.production import ask, reset_for_tests as uag_reset

    uag_reset()
    result = ask({"question": "Why did the recommendation change for AXISBANK?", "entities": ["AXISBANK"]})
    assert result.get("workspace")
    assert result["workspace"].get("href")
    assert "AXISBANK" in result["workspace"]["href"] or "companies" in result["workspace"]["href"]
    assert result["workspace"].get("engine") == "RW-01"
