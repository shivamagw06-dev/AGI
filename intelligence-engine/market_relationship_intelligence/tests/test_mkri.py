"""Sprint 12.3 — Market Relationship Intelligence (MKRI) tests."""

from __future__ import annotations

from market_relationship_intelligence import traces
from market_relationship_intelligence.production import (
    dashboard,
    for_company,
    for_indicator,
    for_sector,
    graph,
    health,
    relationships,
    run,
    search,
)
from market_relationship_intelligence.schema import NO_MKRI_ACTIONS
from market_relationship_intelligence.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_mkri_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "MKRI"
    assert h["phase"] == "12.3"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    for item in NO_MKRI_ACTIONS:
        assert item in h["does_not"]


def test_read_never_rebuilds() -> None:
    out = relationships()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["providers_queried"] == []


def test_run_publishes_evidence_backed_relationships() -> None:
    summary = run(
        enrich_hmkip=False, enrich_hmip=False, enrich_hsip=False, enrich_macro_mri=False
    )
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] >= 20
    assert summary["rejected"] == 0

    pack = relationships()
    assert pack["n"] >= 20
    assert pack["providers_queried"] == []
    for rel in pack["relationships"]:
        assert rel["evidence"]
        assert rel["historical_observations"] >= 1
        assert rel["confidence_pct"] >= 60
        assert rel["providers_queried"] == []
        assert rel["inferred_without_evidence"] is False
        assert rel["average_lag"]
        assert rel["version"] >= 1


def test_repo_breadth_and_vix_chains() -> None:
    run(enrich_hmkip=False, enrich_hmip=False, enrich_hsip=False, enrich_macro_mri=False)
    repo = for_indicator("Repo Rate")
    assert repo["n"] >= 1
    assert repo["collected_on_request"] is False
    assert any("Breadth" in r["target"] or "Liquidity" in r["target"] for r in repo["relationships"])

    vix = for_indicator("India VIX")
    assert vix["n"] >= 2
    assert any(r["target"] == "Small Cap Index" for r in vix["relationships"])
    small = next(r for r in vix["relationships"] if r["target"] == "Small Cap Index")
    assert small["direction"] == "Negative"
    assert small["confidence_pct"] >= 90
    assert small["historical_observations"] >= 20


def test_sector_company_and_search() -> None:
    run(enrich_hmkip=False, enrich_hmip=False, enrich_hsip=False, enrich_macro_mri=False)
    banks = for_sector("Banks")
    assert banks["n"] >= 1

    hdfc = for_company("HDFCBANK")
    assert hdfc["n"] >= 1
    assert any(r["target"] == "HDFCBANK" for r in hdfc["relationships"])

    hits = search(q="liquidity", limit=50)
    assert hits["n"] >= 1
    assert hits["collected_on_request"] is False

    kind_hits = search(kind="cross_asset", limit=50)
    assert kind_hits["n"] >= 2

    flow_hits = search(kind="flows", limit=50)
    assert flow_hits["n"] >= 2


def test_graph_and_transmission_paths() -> None:
    run(enrich_hmkip=False, enrich_hmip=False, enrich_hsip=False, enrich_macro_mri=False)
    g = graph()
    assert g["n_nodes"] >= 12
    assert g["n_edges"] >= 20
    assert g["providers_queried"] == []
    assert g["transmission_paths"]
    blob = str(g["transmission_paths"]).lower()
    assert "repo" in blob or "vix" in blob or "fii" in blob or "usd" in blob

    g2 = graph(start="India VIX", end="Small Cap Index")
    assert "paths_from" in g2
    assert isinstance(g2["paths_from"], list)


def test_no_evidence_rejected() -> None:
    from market_relationship_intelligence.schema import MarketRelationship
    from market_relationship_intelligence.validation import validate_relationship

    bad = MarketRelationship(
        source="X",
        target="Y",
        relationship="Guess",
        kind="cross_asset",
        evidence=[],
        historical_observations=0,
    )
    errors = validate_relationship(bad)
    assert "evidence_required" in errors
    assert "historical_observations_must_be_positive" in errors
    assert "average_lag_required" in errors


def test_mission_control_and_traces() -> None:
    run(enrich_hmkip=False, enrich_hmip=False, enrich_hsip=False, enrich_macro_mri=False)
    for_indicator("FII Buying")
    board = dashboard()
    assert board["board"] == "Market Relationship Intelligence"
    assert board["programme_short"] == "MKRI"
    assert board["principles"]["evidence_backed_only"] is True
    assert board["total_relationships"] >= 20
    assert board["active_relationships"] >= 1
    assert board["confidence_distribution"]
    assert board["recently_validated_relationships"]
    assert board["graph_health"]["nodes"] >= 12
    assert "validation_failures" in board
    assert board["phase"] == "12.3"
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    assert "market_relationship_discovery" in all_names
    assert "market_relationship_validation" in all_names
    assert "market_relationship_scoring" in all_names
    assert "market_relationship_graph" in all_names
    assert "market_relationship_refresh" in all_names
    assert "market_relationship_retrieval" in names or "market_relationship_retrieval" in all_names
