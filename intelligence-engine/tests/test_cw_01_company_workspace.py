"""CW-01 — Company Workspace assembly, provenance, timeline, events, SDK compliance."""

from __future__ import annotations

from office_sdk.contracts import SCHEMA_EVIDENCE_BLOCK, SCHEMA_RESPONSE
from platform_event_bus.dispatcher import reset_bus_for_tests
from platform_event_bus.publisher import publish
from platform_event_bus.schema import (
    EVENT_BUSINESS_QUALITY_UPDATED,
    EVENT_COMPANY_RESEARCH_COMPLETED,
    EVENT_WATCHLIST_COMPANY_ADDED,
)

from company_workspace.events import ensure_subscriptions, reset_subscriptions_for_tests
from company_workspace.production import (
    evidence,
    health,
    research,
    search,
    soft_slice_mission_control,
    timeline,
    workspace,
)
from company_workspace.schema import CW01_SURFACE_ID, CW01_WORKSTREAM_ID, WORKSPACE_SECTIONS
from company_workspace import store as cw_store
from portfolio_office.production import create as po_create
from portfolio_office import store as po_store
from watchlist_office.production import add as wo_add
from watchlist_office.production import create as wo_create
from watchlist_office import store as wl_store


def setup_function(_fn=None):
    reset_bus_for_tests()
    reset_subscriptions_for_tests()
    cw_store.reset_for_tests()
    wl_store.reset_for_tests()
    po_store.reset_for_tests()


def _prebuilt(ticker: str = "TCS") -> dict:
    return {
        "FIRE-01": {
            "ticker": ticker,
            "confidence": 0.81,
            "evidence_ids": ["e-trend-1"],
            "as_of": "2026-01-01T00:00:00+00:00",
            "narrative": "Revenue up",
        },
        "FIRE-02": {
            "ticker": ticker,
            "confidence": 0.7,
            "evidence_ids": ["e-rel-1"],
            "drivers": ["margin"],
        },
        "FIRE-03": {
            "ticker": ticker,
            "confidence": 0.66,
            "evidence_ids": ["e-biz-1"],
            "strategy": "digital",
        },
        "FIRE-04": {
            "ticker": ticker,
            "confidence": 0.72,
            "evidence_ids": ["e-fuse-1"],
            "alignment": "supported",
        },
        "FIRE-05": {
            "ticker": ticker,
            "confidence": 0.6,
            "evidence_ids": ["e-exec-1"],
            "execution_score": 0.55,
        },
        "FIRE-06": {
            "ticker": ticker,
            "confidence": 0.88,
            "evidence_ids": ["e-qual-1"],
            "quality_score": 0.84,
            "pillars": {"moat": 0.9},
        },
    }


def test_health_presentation_only():
    h = health()
    assert h["workstream_id"] == CW01_WORKSTREAM_ID
    assert h["surface_id"] == CW01_SURFACE_ID
    assert h["not_an_engine"] is True
    assert h["not_an_office"] is True
    assert h["runs_fire"] is False
    assert h["buy_sell"] is False
    assert h["presentation_only"] is True
    assert "company.research.completed" in h["subscribes"]
    assert set(WORKSPACE_SECTIONS).issubset(set(h["sections"]))


def test_workspace_assembly_and_sdk_compliance():
    out = workspace(
        "TCS",
        profile={"company": "Tata Consultancy Services", "sector": "IT", "exchange": "NSE"},
        prebuilt=_prebuilt("TCS"),
        use_cache=False,
    )
    assert out["ok"] is True
    assert out["runs_fire"] is False
    assert out["buy_sell"] is False
    resp = out["office_response"]
    assert resp["schema"] == SCHEMA_RESPONSE
    assert resp["report_type"] == "CompanyWorkspace"
    assert resp["metadata"]["guardrails"]["buy_sell"] is False
    assert resp["metadata"]["guardrails"]["recalculates"] is False
    assert resp["routing"]["runs_fire"] is False
    keys = [s["key"] for s in resp["sections"]]
    for required in (
        "overview",
        "business_quality",
        "financial_trends",
        "financial_relationships",
        "management_execution",
        "evidence_alignment",
        "business_strategy",
        "watchlist_status",
        "portfolio_references",
        "confidence_summary",
        "evidence_references",
    ):
        assert required in keys
    # Pass-through: quality score unchanged from prebuilt
    bq = next(s for s in resp["sections"] if s["key"] == "business_quality")
    assert bq["board"]["payload"]["quality_score"] == 0.84
    assert bq["board"]["payload"]["pillars"]["moat"] == 0.9
    for block in resp["provenance"]["blocks"]:
        assert block["schema"] == SCHEMA_EVIDENCE_BLOCK
    assert out["payload"]["overview"]["ticker"] == "TCS"
    assert out["payload"]["overview"]["sector"] == "IT"


def test_evidence_preservation():
    out = workspace("INFY", prebuilt=_prebuilt("INFY"), use_cache=False)
    ev = evidence("INFY")
    assert ev["count"] >= 1
    ids = {r["evidence_id"] for r in ev["references"]}
    assert "e-qual-1" in ids
    assert "e-trend-1" in ids
    # Provenance modules_ok includes FIRE modules
    mods = out["office_response"]["provenance"]["modules_ok"]
    assert "FIRE-06" in mods
    assert "FIRE-01" in mods


def test_watchlist_and_portfolio_context():
    wo_create({"name": "Core"})
    wo_add("Core", {"ticker": "RELIANCE", "priority": "High", "tags": ["energy"], "notes": "Watch"})
    po_create(
        {
            "name": "India Core",
            "holdings": [
                {
                    "ticker": "RELIANCE",
                    "quantity": 100,
                    "average_cost": 2500,
                    "sector": "Energy",
                }
            ],
        }
    )
    out = workspace("RELIANCE", prebuilt=_prebuilt("RELIANCE"), use_cache=False)
    wl = next(s for s in out["sections"] if s["key"] == "watchlist_status")
    assert wl["board"]["count"] == 1
    assert wl["board"]["watchlists"][0]["priority"] == "High"
    assert wl["board"]["watchlists"][0]["tags"] == ["energy"]
    pf = next(s for s in out["sections"] if s["key"] == "portfolio_references")
    assert pf["board"]["count"] == 1
    assert pf["board"]["memberships"][0]["ticker"] == "RELIANCE"
    assert pf["board"]["memberships"][0]["sector"] == "Energy"


def test_timeline_ordering_and_event_refresh():
    ensure_subscriptions()
    workspace("TCS", prebuilt=_prebuilt("TCS"), use_cache=False)
    publish(
        EVENT_COMPANY_RESEARCH_COMPLETED,
        producer="io-01",
        payload={
            "ticker": "TCS",
            "package_type": "Institutional Brief",
            "modules_invoked": ["FIRE-01", "FIRE-06"],
            "module_payloads": {
                "FIRE-06": {"quality_score": 0.91, "confidence": 0.9, "evidence_ids": ["e-q2"]},
            },
        },
    )
    publish(
        EVENT_BUSINESS_QUALITY_UPDATED,
        producer="fire-06",
        payload={"ticker": "TCS", "quality": {"quality_score": 0.91, "confidence": 0.9}},
    )
    publish(
        EVENT_WATCHLIST_COMPANY_ADDED,
        producer="wo-01",
        payload={"ticker": "TCS", "watchlist_id": "core", "priority": "Medium"},
    )
    tl = timeline("TCS")
    assert tl["count"] >= 3
    ats = [e["at"] for e in tl["events"] if e.get("at")]
    assert ats == sorted(ats)
    # Research cache populated without running IO
    hist = research("TCS")
    assert hist["count"] >= 1
    assert hist["latest"]["package_type"] == "Institutional Brief"
    # Refresh invalidated cache; reassemble picks up module cache from event
    out = workspace("TCS", use_cache=False)
    bq = next(s for s in out["sections"] if s["key"] == "business_quality")
    assert bq["board"]["available"] is True
    assert bq["board"]["payload"]["quality_score"] == 0.91


def test_section_search():
    workspace("HDFCBANK", prebuilt=_prebuilt("HDFCBANK"), use_cache=False)
    found = search("HDFCBANK", "Business Quality", scope="section")
    assert found["counts"]["sections"] >= 1
    keys = [s["key"] for s in found["sections"]]
    assert "business_quality" in keys
    ev = search("HDFCBANK", "e-trend-1", scope="evidence")
    assert ev["counts"]["evidence"] >= 1


def test_mission_control_panels():
    workspace("TCS", prebuilt=_prebuilt("TCS"), use_cache=False)
    slice_ = soft_slice_mission_control()
    assert slice_["workstream_id"] == CW01_WORKSTREAM_ID
    assert "companies_viewed" in slice_["panels"]
    assert "workspace_refreshes" in slice_["panels"]
    assert "coverage" in slice_["panels"]
    assert "evidence_completeness" in slice_["panels"]
    assert slice_["presentation_only"] is True


def test_no_analysis_without_prebuilt():
    out = workspace("UNKNOWNCO", use_cache=False)
    assert out["ok"] is True
    assert out["runs_fire"] is False
    bq = next(s for s in out["sections"] if s["key"] == "business_quality")
    assert bq["board"]["available"] is False
    outstanding = next(s for s in out["sections"] if s["key"] == "outstanding_questions")
    assert outstanding["board"]["questions"]
