"""Sprint 12.2 — Historical Market Intelligence Platform (HMKIP) tests."""

from __future__ import annotations

from continuous_market_knowledge.schema import MARKET_UNIVERSE
from historical_market_intelligence import traces
from historical_market_intelligence.normalization import normalize_observation
from historical_market_intelligence.production import (
    breadth,
    dashboard,
    flows,
    health,
    history,
    liquidity,
    market,
    regimes,
    run,
    search,
    timeline,
    volatility,
)
from historical_market_intelligence.schema import (
    NO_HMKIP_ACTIONS,
    STORAGE_NAMESPACES,
    RawHistoricalMarketObservation,
)
from historical_market_intelligence.store import STORE, reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_hmkip_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "HMKIP"
    assert h["phase"] == "12.2"
    assert h["immutable_store"] is True
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["market_count"] == len(MARKET_UNIVERSE)
    for item in NO_HMKIP_ACTIONS:
        assert item in h["does_not"]
    for ns in STORAGE_NAMESPACES:
        assert ns in h["namespaces"]


def test_read_never_collects() -> None:
    out = history()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["providers_queried"] == []
    miss = market("india_equity")
    assert miss["found"] is False
    assert miss["collected_on_request"] is False


def test_ingestion_builds_immutable_series_and_timelines() -> None:
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["immutable_store"] is True
    assert summary["providers_queried"] == []
    assert summary["published_total"] >= 100
    assert summary["timelines"] >= len(MARKET_UNIVERSE)

    india = market("india_equity")
    assert india["found"] is True
    assert india["providers_queried"] == []
    assert india["timeline"] is not None
    assert india["timeline"]["completeness_pct"] >= 50
    events_labels = [n.get("event") for n in india["timeline"]["nodes"] if n.get("event")]
    assert any(
        "COVID" in (e or "") or "GFC" in (e or "") or "Dot-com" in (e or "")
        for e in events_labels
    )


def test_india_timeline_regime_anchors() -> None:
    run()
    tl = timeline(market="NIFTY", indicator="Market Health")
    assert tl["n"] >= 1
    nodes = tl["timelines"][0]["nodes"]
    labels = {n["year"]: n.get("event") for n in nodes}
    assert labels.get(2008) == "2008 GFC"
    assert labels.get(2020) == "2020 COVID Crash"
    assert labels.get(2000) == "Dot-com Crash"
    assert labels.get(2016) == "2016 Demonetisation"


def test_immutable_no_overwrite_on_rerun() -> None:
    first = run()
    n1 = first["published_total"]
    second = run()
    assert second["published_total"] == n1
    assert second["duplicate_checksums_skipped"] >= n1
    assert second["published_new"] == 0


def test_revision_appends_new_version() -> None:
    run()
    raw = RawHistoricalMarketObservation(
        source="agi_internal_historical",
        market_key="india_equity",
        market_label="India Equity Market",
        category="Health",
        indicator="Market Health",
        value=64.0,  # revised vs seeded FY2026 62.0
        period="FY2026",
        unit="index",
        publication_date="2026-03-31",
        market_regime="Sideways",
    )
    prior_n = STORE.coverage()["total_observations"]
    hmkto = normalize_observation(raw, revision_note="fy26_revision")
    STORE.append(hmkto)
    assert STORE.coverage()["total_observations"] == prior_n + 1
    versions = STORE.versions("india_equity", "Market Health", "FY2026")
    assert len(versions) >= 2
    assert versions[-1].version >= 2


def test_domain_endpoints_and_search() -> None:
    run()
    assert regimes(market="india_equity")["n"] >= 1
    assert breadth()["n"] >= 1
    assert liquidity()["n"] >= 1
    assert volatility()["n"] >= 1
    assert flows()["n"] >= 1
    hit = search(q="COVID", market="india_equity")
    assert hit["n"] >= 1
    assert hit["collected_on_request"] is False
    assert hit["providers_queried"] == []


def test_namespaces_and_dashboard() -> None:
    run()
    cov = STORE.coverage()
    assert cov["by_namespace"]["historical_market_cycles"] >= 1
    assert cov["by_namespace"]["historical_market_breadth"] >= 1
    assert cov["by_namespace"]["historical_market_volatility"] >= 1
    assert cov["unique_markets"] == len(MARKET_UNIVERSE)
    board = dashboard()
    assert board["board"] == "Historical Market"
    assert board["principles"]["immutable_store"] is True
    assert board["historical_coverage"]["total_observations"] >= 100
    assert board["timeline_completeness"]["average_completeness_pct"] > 0
    assert board["phase"] == "12.2"
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "historical_market_collection" in names
    assert "historical_market_validation" in names
    assert "historical_market_normalization" in names
    assert "historical_market_timeline" in names
    assert "historical_market_publication" in names
