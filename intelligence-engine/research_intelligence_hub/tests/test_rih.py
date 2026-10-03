"""AGIB v4.0 — Research Intelligence Hub tests."""

from __future__ import annotations

from research_intelligence_hub import traces
from research_intelligence_hub.production import (
    build,
    dashboard,
    graph,
    health,
    history,
    hub,
    list_hubs,
    run,
)
from research_intelligence_hub.schema import LINK_DOMAINS, NO_RIH_ACTIONS
from research_intelligence_hub.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_rih_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "RIH"
    assert h["phase"] == "4.0"
    assert h["is_intelligence_hub"] is True
    assert h["is_document"] is False
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["primary_knowledge_object"] == "ResearchObject"
    for item in NO_RIH_ACTIONS:
        assert item in h["does_not"]
    for domain in LINK_DOMAINS:
        assert domain in h["link_domains"]
    assert "research_hub_publication" in h["langsmith_traces"]


def test_run_publishes_intelligence_hubs() -> None:
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] >= 3
    assert "rih_rbi_easing_watch" in summary["per_hub"]


def test_hub_is_intelligence_object_with_all_sections() -> None:
    run(note_id="rih_rbi_easing_watch")
    pack = hub("rih_rbi_easing_watch")
    assert pack["is_intelligence_object"] is True
    assert pack["is_document"] is False
    assert pack["is_recommendation"] is False
    assert pack["providers_queried"] == []
    assert pack["executive_summary"]
    assert pack["investment_thesis"]
    assert pack["why_it_matters"]
    assert pack["companies"]
    assert any(c["id"] == "ICICIBANK" for c in pack["companies"])
    assert pack["sectors"]
    assert pack["markets"]
    assert pack["macro_topics"]
    assert pack["historical_context"]
    assert pack["relationships"]
    assert pack["historical_analogues"]
    assert pack["forecast"]["scenarios"]
    assert set(s["scenario"] for s in pack["forecast"]["scenarios"]) == {"Bull", "Base", "Bear"}
    assert pack["forecast"]["predicts_single_path"] is False
    assert pack["supporting_evidence"]
    assert all(e.get("traceable") is True for e in pack["supporting_evidence"])
    assert pack["navigation"]
    assert "forecast" in pack["navigation"]


def test_build_from_arbitrary_article() -> None:
    out = build(
        note_id="cms_demo_note",
        headline="Oil spike risk for Auto and Airlines",
        body="Crude oil and USD strength can pressure Auto margins. TATAMOTORS watches steel and oil.",
        session="Afternoon",
        tickers=["TATAMOTORS"],
        persist=True,
    )
    assert out["id"] == "cms_demo_note"
    assert out["mode"] == "published"
    assert any(c["id"] == "TATAMOTORS" for c in out["companies"])
    assert any(m["label"] == "Commodities" for m in out["macro_topics"]) or out["macro_topics"]
    assert out["forecast"]["probability_distribution"]
    assert sum(out["forecast"]["probability_distribution"].values()) == 100


def test_graph_rooted_at_research_note() -> None:
    run(note_id="rih_it_usd_sensitivity")
    g = graph("rih_it_usd_sensitivity")
    assert g["note_id"] == "rih_it_usd_sensitivity"
    root = next(n for n in g["nodes"] if n.get("root"))
    assert root["kind"] == "research_note"
    assert any(e["source"] == g["note_id"] for e in g["edges"])
    assert g["providers_queried"] == []


def test_list_hubs_and_history() -> None:
    run()
    run(note_id="rih_rbi_easing_watch")
    listed = list_hubs()
    assert listed["n"] >= 1
    assert listed["primary_knowledge_object"] == "ResearchObject"
    hist = history("rih_rbi_easing_watch")
    assert hist["n"] >= 2
    versions = [v["version"] for v in hist["versions"]]
    assert versions == sorted(versions, reverse=True)


def test_dashboard_and_traces() -> None:
    board = dashboard()
    assert board["board"] == "Research Intelligence Hub"
    assert board["principles"]["research_is_primary_knowledge_object"] is True
    assert board["principles"]["note_is_intelligence_hub"] is True
    assert board["hub_count"] >= 1
    assert board["link_coverage"]["companies"] >= 1
    assert "research_hub_ingest" in board["langsmith_traces"]
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    for required in (
        "research_hub_ingest",
        "research_entity_extraction",
        "research_link_assembly",
        "research_relationship_retrieval",
        "research_analogue_retrieval",
        "research_forecast_attachment",
        "research_evidence_attachment",
        "research_hub_publication",
    ):
        assert required in names or required in all_names


def test_no_live_providers() -> None:
    out = hub("rih_global_risk_off")
    assert out["providers_queried"] == []
    assert out["collected_on_request"] is False
    assert "query_live_market_feeds" in NO_RIH_ACTIONS
