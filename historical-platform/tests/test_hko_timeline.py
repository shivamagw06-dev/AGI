"""Sprint 8.2 — Historical Knowledge Objects & Timeline Intelligence tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.collectors.yahoo.historical import YahooHistoricalCollector
from app.config.settings import Settings
from app.main import create_app
from app.pipeline.orchestrator import HistoricalAcquisitionPipeline
from app.storage.db import HipStore
from app.timeline.builder import TimelineBuilder


def _settings(tmp_path: Path, watchlist: tuple[str, ...] = ("INFY",)) -> Settings:
    return Settings(
        db_path=tmp_path / "hip.db",
        live_collectors_enabled=False,
        watchlist=watchlist,
        min_daily_bars=40,
        min_quarterly_financials=8,
        min_annual_financials=11,
    )


def _bootstrapped_client(tmp_path: Path):
    settings = _settings(tmp_path)
    app = create_app(settings)
    client = TestClient(app)
    client.__enter__()
    boot = client.post("/v1/internal/bootstrap")
    assert boot.status_code == 200
    body = boot.json()
    assert body["historical_objects"] > 0
    assert body["timeline_events"] > 0
    assert body.get("timelines") is not None
    return client


def test_infosys_company_timeline_narrative(tmp_path: Path) -> None:
    """Every company gets a chronological narrative (IPO → crises → AI)."""
    client = _bootstrapped_client(tmp_path)
    try:
        resp = client.get("/v1/history/timeline/INFY")
        assert resp.status_code == 200
        body = resp.json()
        assert body["providers_queried"] == []
        titles = [e["title"] for e in body["timeline"]]
        for expected in ("IPO", "Global Financial Crisis", "COVID", "AI Transformation"):
            assert expected in titles
        years = [e["year"] for e in body["timeline"]]
        assert years == sorted(years)
        narrative_titles = [n["title"] for n in body["narrative"]]
        assert "IPO" in narrative_titles
        # COVID → IT → Infosys → revenue → margins → valuation links present
        rels = body["relationships"]
        assert any("COVID" in (r.get("from_key") or "") or "COVID" in (r.get("to_key") or "") for r in rels)
    finally:
        client.__exit__(None, None, None)


def test_hko_shaped_financials_and_events(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        fins = client.get("/v1/history/financials/INFY").json()
        assert fins["providers_queried"] == []
        assert len(fins["items"]) >= 11
        hko = fins["items"][0]["hko"]
        assert hko["object_type"] == "HistoricalFinancialStatement"
        assert "revenue" in hko
        assert hko["company"] == "INFY"

        company = client.get("/v1/history/company/INFY").json()
        assert company["providers_queried"] == []
        assert company["timeline"]
        assert company["timeline_completeness"]["status"] in {"Complete", "Partial"}
    finally:
        client.__exit__(None, None, None)


def test_compare_infosys_today_with_fy2018(tmp_path: Path) -> None:
    """Success path: KRIG/Ask compares Infosys today with FY2018 from store only."""
    client = _bootstrapped_client(tmp_path)
    try:
        resp = client.post(
            "/v1/history/compare",
            json={"symbol": "INFY", "as_of_period": "FY2018"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["providers_queried"] == []
        assert body["as_of_period"] == "FY2018"
        assert body["historical_financials"] is not None
        assert body["historical_financials"]["effective_date"] == "FY2018"
        assert body["current_company_knowledge_tip"] is not None
        assert body["bundle"]["historical_timeline"]
        assert body["bundle"]["historical_financials"]["object_type"] == "HistoricalFinancialStatement"
    finally:
        client.__exit__(None, None, None)


def test_sector_market_macro_timelines(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        sector = client.get("/v1/history/timeline/sector/information_technology").json()
        assert sector["providers_queried"] == []
        titles = [e["title"] for e in sector["timeline"]]
        assert "Financial Crisis" in titles
        assert "AI Spending Boom" in titles

        market = client.get("/v1/history/timeline/market").json()
        assert "Demonetisation" in [e["title"] for e in market["timeline"]]
        assert "COVID Crash" in [e["title"] for e in market["timeline"]]

        macro = client.get("/v1/history/timeline/macro").json()
        assert any(e["title"] == "Inflation Cycle" for e in macro["timeline"])
    finally:
        client.__exit__(None, None, None)


def test_historical_records_immutable_versioned(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = HipStore(settings.db_path)
    pipeline = HistoricalAcquisitionPipeline(store)
    collector = YahooHistoricalCollector(symbols=["INFY"], live=False)
    first = pipeline.run_collector(collector, mode="bootstrap")
    second = pipeline.run_collector(collector, mode="incremental")
    assert len(first.objects) > 0
    assert len(second.duplicates) == len(second.raw_events)
    # Financial years remain individually addressable
    fins = store.list_financials("INFY", period_kind="annual")
    periods = [f["effective_date"] for f in fins]
    assert "FY2018" in periods
    assert "FY2019" in periods
    assert periods == sorted(periods)
    # Timeline rebuild does not erase HKO
    before = store.count_objects()
    TimelineBuilder(store).rebuild_all(["INFY"])
    assert store.count_objects() == before
    assert store.count_timeline_events() > 0


def test_mission_control_historical_board(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        resp = client.get("/v1/history/mission-control")
        assert resp.status_code == 200
        body = resp.json()
        assert body["board"] == "Historical Intelligence"
        assert body["principles"]["immutable_history"] is True
        assert body["principles"]["providers_never_on_ask_path"] is True
        assert any(c["company_symbol"] == "INFY" for c in body["companies"])
        infy = next(c for c in body["companies"] if c["company_symbol"] == "INFY")
        assert infy["timeline_events"] > 0
        assert infy["years_ingested"]
        # Trace names from Sprint 8.2 / 8.3 contracts
        names = {t["name"] for t in body["retrieval_performance"]["traces"]}
        assert (
            "historical_ingestion" in names
            or "timeline_generation" in names
            or "historical_relationship_builder" in names
        )
    finally:
        client.__exit__(None, None, None)


def test_service_version_hko(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        health = client.get("/healthz").json()
        assert health["service"] == "hip-hai"
        assert health["version"] == "0.4.0"
