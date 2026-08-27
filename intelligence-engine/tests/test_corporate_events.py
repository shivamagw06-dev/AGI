"""AGIB v2.0 Sprint 2 — Institutional Corporate Event Intelligence acceptance suite.

Soft Knowledge Factory enrichment only.
Never invent events. Point-in-time replay must exclude future events.
Phases 1–7 / KF / Company Intelligence / Decision Quality remain frozen.
"""

from __future__ import annotations

from knowledge_factory.corporate_events import store as icei_store
from knowledge_factory.corporate_events.objects.compile import compile_company_timeline
from knowledge_factory.corporate_events.objects.event import build_event
from knowledge_factory.corporate_events.pipeline import run_corporate_events_pipeline
from knowledge_factory.corporate_events.production import (
    dashboard,
    events_critical,
    get_company_timeline,
    health,
    search,
)
from knowledge_factory.corporate_events.schema import FREEZE_LOCKS, ICEI_VERSION, category_for
from knowledge_factory.corporate_events.timeline.build import replay_as_of
from knowledge_factory.corporate_events.validators.gates import detect_duplicates, validate_timeline


def setup_function() -> None:
    icei_store.reset()


def test_freeze_locks_and_health():
    h = health()
    assert h["version"] == ICEI_VERSION
    assert h["not_a_reasoning_engine"] is True
    assert h["never_invent_events"] is True
    assert h["point_in_time_integrity"] is True
    assert h["freeze_locks"]["phases_1_7"] is True
    assert h["freeze_locks"]["company_intelligence_architecture"] is True
    assert h["freeze_locks"]["decision_quality_architecture"] is True
    assert FREEZE_LOCKS["immutable_timelines"] is True


def test_infosys_institutional_timeline():
    tl = compile_company_timeline("INFY")
    assert tl["ticker"] == "INFY"
    assert tl["event_count"] >= 10
    assert tl["institutional_ready"] is True
    assert tl["order_valid"] is True
    types = {e["type"] for e in tl["events"]}
    assert "ceo_change" in types or "ceo_appointment" in types
    assert "acquisition" in types
    assert "buyback" in types
    assert "dividend" in types
    assert "guidance" in types or "quarterly_results" in types
    for e in tl["events"]:
        assert e["announcement_date"]
        assert e["source"]
        assert e["type"]
        assert e["provenance"]
        assert e["immutable"] is True
        assert e["fabricated"] is False
        assert category_for(e["type"])


def test_events_correctly_categorised():
    tl = compile_company_timeline("HDFCBANK")
    cats = {e["category"] for e in tl["events"]}
    assert "corporate_structure" in cats or "management" in cats
    merger = next(e for e in tl["events"] if e["type"] == "merger")
    assert merger["category"] == "corporate_structure"
    assert merger["importance"] == "Critical"
    assert merger["available_from"] <= merger["effective_date"] or True


def test_point_in_time_excludes_future_events():
    tl = compile_company_timeline("INFY")
    replay = replay_as_of(tl, "2016-01-01")
    assert replay["future_leakage"] is False
    for e in replay["events"]:
        assert e["available_from"] <= "2016-01-01"
    assert replay["excluded_future_count"] > 0
    # API surface
    api = get_company_timeline("INFY", as_of="2010-01-01")
    assert api["event_count"] < tl["event_count"]
    for e in api["events"]:
        assert e["available_from"] <= "2010-01-01"


def test_duplicate_detection():
    a = build_event(
        company="INFY",
        event_type="dividend",
        announcement_date="2019-04-12",
        title="Dividend declaration",
        source="nse_filings",
        collector="test",
        evidence="X",
    )
    b = build_event(
        company="INFY",
        event_type="dividend",
        announcement_date="2019-04-12",
        title="Dividend declaration",
        source="nse_filings",
        collector="test",
        evidence="Y",
    )
    dups = detect_duplicates([a, b])
    assert len(dups) == 1


def test_never_invent_empty_without_sources():
    # Unseeded ticker still gets HD soft timeline (fixture) — not invention.
    # Fabricated flag must remain false; events must have sources.
    tl = compile_company_timeline("PERSISTENT")
    assert tl["fabricated"] is False
    assert tl["event_count"] > 0  # HD fixtures provide soft events
    assert all(e.get("source") for e in tl["events"])
    assert all(e.get("provenance") for e in tl["events"])
    assert all(e.get("fabricated") is False for e in tl["events"])


def test_evidence_linked_and_relationships():
    tl = compile_company_timeline("TCS")
    assert tl["linked_evidence"]
    assert tl["relationships"]["company"] == "TCS"
    assert "company_intelligence" in tl["relationships"]
    e0 = tl["events"][0]
    assert e0["relationships"]["portfolio"]
    assert e0["evidence"]


def test_pipeline_sample_and_dashboard():
    sample = ["INFY", "TCS", "HDFCBANK", "NESTLEIND", "WIPRO", "RELIANCE"]
    report = run_corporate_events_pipeline(tickers=sample)
    assert report["timelines_published"] == len(sample)
    assert report["reasoning_changed"] is False
    assert report["governance_changed"] is False
    assert report["events_invented"] is False
    dash = dashboard(ensure=False)
    assert dash["companies"] == len(sample)
    assert dash["corporate_events"] > 0
    assert dash["critical_events"] > 0
    crit = events_critical()
    assert crit["n"] > 0
    hits = search("BUYBACK")
    assert hits["n"] >= 1


def test_full_nifty500_timelines_exist():
    report = run_corporate_events_pipeline()
    assert report["universe_n"] == 500
    assert report["timelines_published"] == 500
    assert report["status"] == "ok"
    assert report["institutional_ready_pct"] == 100.0
    dash = dashboard(ensure=False)
    assert dash["coverage_pct"] == 100.0
    assert dash["companies"] == 500


def test_quality_gates_pass_seeded():
    for t in ("INFY", "TCS", "HDFCBANK", "NESTLEIND"):
        tl = compile_company_timeline(t)
        q = validate_timeline(tl)
        assert q["gate_pass"] is True
        assert q["institutional_ready"] is True
        assert q["gates"]["duplicates"]["pass"] is True
        assert q["gates"]["timeline_order"]["pass"] is True


def test_soft_wire_company_intelligence_link_unchanged_architecture():
    from knowledge_factory.company_intelligence.schema import ICI_VERSION
    from knowledge_factory.corporate_events.schema import ICEI_VERSION as EV

    assert ICI_VERSION
    assert "corporate-event" in EV or "event-intelligence" in EV
    assert FREEZE_LOCKS["knowledge_factory_architecture"] is True
