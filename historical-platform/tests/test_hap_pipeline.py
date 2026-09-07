"""Sprint 8.1 — Historical Acquisition Platform tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.collectors.yahoo.historical import YahooHistoricalCollector, default_yahoo_fixture
from app.config.settings import Settings
from app.main import create_app
from app.pipeline.orchestrator import HistoricalAcquisitionPipeline
from app.storage.db import HipStore


def _settings(tmp_path: Path, watchlist: tuple[str, ...] = ("INFY",)) -> Settings:
    return Settings(
        db_path=tmp_path / "hip.db",
        live_collectors_enabled=False,
        watchlist=watchlist,
        # Fixture prices are sparse (~44 bars); keep floor low for Complete/Partial checks
        min_daily_bars=40,
        min_quarterly_financials=8,
        min_annual_financials=11,
    )


def test_coverage_policy_exposed(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        resp = client.get("/v1/historical/coverage/policy")
        assert resp.status_code == 200
        body = resp.json()
        assert body["policy"] == "historical_coverage_v1"
        cats = {t["category"] for t in body["targets"]}
        assert "daily_ohlcv" in cats
        assert "quarterly_financials" in cats
        assert "company_ir_reports" in cats


def test_yahoo_bootstrap_archives_and_builds(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = HipStore(settings.db_path)
    pipeline = HistoricalAcquisitionPipeline(store)
    result = pipeline.run_collector(
        YahooHistoricalCollector(symbols=["INFY"], live=False),
        mode="bootstrap",
        symbols=["INFY"],
    )
    assert len(result.accepted) >= 5
    assert len(result.objects) > 20
    assert store.count_raw() >= 5
    assert store.count_objects() > 20
    entity = store.get_entity("INFY")
    assert entity is not None
    assert entity["sector_key"] == "information_technology"
    assert "NIFTY50" in entity["index_membership"]


def test_append_only_duplicate_checksum(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = HipStore(settings.db_path)
    pipeline = HistoricalAcquisitionPipeline(store)
    collector = YahooHistoricalCollector(symbols=["INFY"], live=False)
    first = pipeline.run_collector(collector, mode="bootstrap")
    second = pipeline.run_collector(collector, mode="incremental")
    assert len(first.accepted) > 0
    assert len(second.duplicates) == len(second.raw_events)
    assert len(second.accepted) == 0


def test_infosys_revenue_fy2015_fy2025_from_store_only(tmp_path: Path) -> None:
    """Success example: IE retrieves Infosys revenue history without external providers."""
    settings = _settings(tmp_path)
    app = create_app(settings)
    with TestClient(app) as client:
        boot = client.post("/v1/internal/bootstrap")
        assert boot.status_code == 200
        assert boot.json()["historical_objects"] > 0

        rev = client.get(
            "/v1/historical/company/INFY/revenue",
            params={"from_period": "FY2015", "to_period": "FY2025"},
        )
        assert rev.status_code == 200
        body = rev.json()
        assert body["providers_queried"] == []
        assert body["company_symbol"] == "INFY"
        periods = [row["period"] for row in body["series"] if str(row["period"]).startswith("FY")]
        # annual FY labels present
        annual = [p for p in periods if "Q" not in p]
        assert "FY2015" in annual
        assert "FY2025" in annual
        assert len(annual) >= 11
        # growth computed after first year
        grown = [r for r in body["series"] if r.get("revenue_growth_pct") is not None]
        assert len(grown) >= 10
        # valuation available on cycles
        assert any((r.get("valuation") or r.get("pe")) for r in body["series"])

        hist = client.get("/v1/historical/company/INFY")
        assert hist.status_code == 200
        assert hist.json()["providers_queried"] == []
        assert hist.json()["entity"]["company_symbol"] == "INFY"

        cov = client.get("/v1/historical/coverage/INFY").json()
        assert cov["categories"]["annual_financials"]["present"] >= 11
        assert cov["categories"]["annual_financials"]["status"] in {"Complete", "Partial"}


def test_integrity_never_overwrites_financial_period(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = HipStore(settings.db_path)
    pipeline = HistoricalAcquisitionPipeline(store)
    fixture = default_yahoo_fixture("INFY")
    # first ingest
    pipeline.run_collector(
        YahooHistoricalCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": fixture}),
        mode="bootstrap",
    )
    # correction: mutate revenue for FY2020 but change payload enough for new checksum
    fixture2 = default_yahoo_fixture("INFY")
    for row in fixture2["financials_annual"]:
        if row["period"] == "FY2020":
            row["revenue"] = 999999.0
            row["correction"] = True
    fixture2["correction_marker"] = "v2"
    # Need new category payloads — rebuild collector events via unique top-level key
    # Force new checksums by altering each category payload slightly through fixture fields
    for key in ("prices_daily", "financials_annual", "financials_quarterly", "balance_sheets", "cash_flows", "dividends", "splits", "news"):
        if isinstance(fixture2.get(key), list) and fixture2[key]:
            fixture2[key] = list(fixture2[key])
            if isinstance(fixture2[key][0], dict):
                fixture2[key][0] = {**fixture2[key][0], "_v": 2}

    pipeline.run_collector(
        YahooHistoricalCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": fixture2}),
        mode="correction",
    )
    fins = store.list_financials("INFY", period_kind="annual")
    fy2020 = [f for f in fins if f["effective_date"] == "FY2020"]
    versions = sorted({f["version"] for f in fy2020})
    assert len(versions) >= 2
    assert max(versions) >= 2


def test_all_collectors_bootstrap(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, watchlist=("INFY", "TCS")))
    with TestClient(app) as client:
        summary = client.post("/v1/internal/bootstrap").json()["summary"]
        assert "YahooHistoricalCollector" in summary
        assert "NSEHistoricalCollector" in summary
        assert "BSEHistoricalCollector" in summary
        assert "CompanyIRHistoricalCollector" in summary
        reports_resp = client.get("/v1/historical/company/INFY/reports").json()
        assert len(reports_resp["items"]) >= 10
        assert reports_resp["providers_queried"] == []
