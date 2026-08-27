"""Forecast Provider Integration — India-first Knowledge Platform tests."""

from __future__ import annotations

from forecast_provider_integration import traces
from forecast_provider_integration.production import (
    company_knowledge,
    dashboard,
    enrich_for_forecast,
    health,
    provider_health,
    publish_company,
    refresh_snapshot,
)
from forecast_provider_integration.schema import FORECAST_FORBIDDEN_DIRECT_CALLS, REFRESH_POLICY
from forecast_provider_integration.store import reset
from institutional_forecast_intelligence.production import company as ifi_company
from institutional_forecast_intelligence.production import market as ifi_market


def setup_function() -> None:
    reset()
    traces.clear()


def test_fpi_health_architecture() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "FPI"
    assert h["primary_live_market"] == "groww"
    assert h["primary_research"] == "yahoo"
    assert h["forecast_direct_provider_calls"] is False
    for p in FORECAST_FORBIDDEN_DIRECT_CALLS:
        assert p in h["forbidden_on_forecast_path"]


def test_publish_company_static_dynamic_layers() -> None:
    out = publish_company("INFY")
    assert out["entity"] == "INFY"
    assert out["static"]["business_profile"]["name"]
    assert out["static"]["financial_statements"]
    assert out["static"]["research"]["company_ir_documents"]
    assert out["static"]["research"]["nse_events"]
    assert out["dynamic"]["snapshot"]["source_provider"] == "groww"
    assert out["dynamic"]["snapshot"]["ltp"] is not None
    assert out["layers"]["static"] is True
    assert out["layers"]["dynamic_market_state"] is True
    assert out["forecast_may_direct_call_providers"] is False


def test_stale_snapshot_refresh_only() -> None:
    first = refresh_snapshot("INFY")
    assert first["refreshed"] is True
    assert first["forecast_direct_provider_call"] is False
    assert first["snapshot"]["source_provider"] == "groww"

    second = refresh_snapshot("INFY")
    assert second["refreshed"] is False
    assert second["reason"] == "snapshot_fresh"
    assert second["provider_called"] is None

    forced = refresh_snapshot("INFY", force=True)
    assert forced["refreshed"] is True
    assert forced["reason"] == "forced"


def test_provider_health_dashboard() -> None:
    publish_company("INFY")
    board = provider_health()
    assert board["groww_connection_status"]
    assert board["yahoo_finance_status"]
    assert board["nse_collector_status"] == "healthy"
    assert board["bse_collector_status"] == "healthy"
    assert board["company_ir_collector_status"] == "healthy"
    assert board["forecast_may_call_providers_directly"] is False
    assert "groww_live_market" in board["refresh_policy"]
    assert board["refresh_policy"]["groww_live_market"]["fallback"] == "yahoo"
    names = {p["provider"] for p in board["providers"]}
    assert names == {"groww", "yahoo", "nse", "bse", "company_ir"}


def test_ifi_bundle_consumes_knowledge_not_raw_apis() -> None:
    out = ifi_company("INFY")
    assert out["providers_queried"] == []
    assert out["provenance"]["forecast_direct_provider_calls"] is False
    assert out["provenance"]["controlled_refresh"] == "market_snapshot_when_stale"
    ck = out["current_knowledge"]
    assert ck.get("static_knowledge")
    assert ck.get("dynamic_market_state") or ck.get("market_snapshot")
    assert (out.get("market_intelligence") or {}).get("live_snapshot")
    snap = out["market_intelligence"]["live_snapshot"]
    assert snap["source_provider"] == "groww"
    assert snap["ltp"] is not None
    # Freshness tip present
    assert "market_snapshot" in (out.get("knowledge_freshness") or {})


def test_ifi_market_bundle_snapshot() -> None:
    out = ifi_market()
    assert out["providers_queried"] == []
    assert (out.get("market_intelligence") or {}).get("live_snapshot")
    assert out["market_intelligence"]["live_snapshot"]["entity"] == "NIFTY"


def test_enrich_bridge_forbids_direct_calls() -> None:
    tip = enrich_for_forecast(
        scope="company",
        entity="TCS",
        catalog_current={"ticker": "TCS", "name": "TCS"},
        catalog_market={"market": "NIFTY"},
    )
    assert tip["providers_queried"] == []
    assert set(tip["forbidden_direct_calls"]) == set(FORECAST_FORBIDDEN_DIRECT_CALLS)
    assert tip["market_snapshot"]["ltp"] is not None


def test_traces_present() -> None:
    publish_company("HDFCBANK")
    refresh_snapshot("NIFTY", scope="market", force=True)
    ifi_company("INFY")
    board = dashboard()
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "groww_market_refresh" in names
    assert "yahoo_financial_refresh" in names
    assert "forecast_market_snapshot" in names
    assert "knowledge_refresh" in names
    assert "forecast_bundle_generation" in names


def test_refresh_policy_intervals() -> None:
    assert REFRESH_POLICY["groww_live_market"]["snapshot_interval_sec"] == 45
    assert REFRESH_POLICY["nse_corporate_events"]["interval_sec"] == 30
    assert REFRESH_POLICY["bse_corporate_events"]["interval_sec"] == 30
    assert REFRESH_POLICY["company_ir_documents"]["market_hours_interval_sec"] == 600
    assert REFRESH_POLICY["yahoo_fundamentals"]["stale_after_sec"] == 86400


def test_company_knowledge_api() -> None:
    row = company_knowledge("RELIANCE")
    assert row["found"] is True or row.get("object")
    # Second call hits store
    row2 = company_knowledge("RELIANCE")
    assert row2["found"] is True
