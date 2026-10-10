"""Ops observability — collector health, heat map, audit, throughput."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    from knowledge_factory.historical_depth import store as hd_store
    from live_data import store as lidi_store

    hd_store.reset_store()
    lidi_store.reset_runtime()
    yield
    hd_store.reset_store()
    lidi_store.reset_runtime()


def test_ops_dashboard_shapes(monkeypatch):
    from continuous_gather_learn.ops_observability import ops_dashboard
    from knowledge_factory.historical_depth.collectors import collect_entity_history
    from knowledge_factory.historical_depth import queue as bf_queue

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY", "TCS"],
    )
    monkeypatch.setattr(bf_queue, "supported_universe", lambda: ["INFY", "TCS"])
    collect_entity_history("INFY", prefer_live=False)
    collect_entity_history("TCS", prefer_live=False)
    bf_queue.ensure_queue(force_refresh=True)

    board = ops_dashboard()
    assert board["ops_version"]
    assert len(board["collector_health"]) >= 5
    assert {r["collector"] for r in board["collector_health"]} >= {
        "NSE Bhavcopy",
        "BSE Actions",
        "Company IR",
    }
    heat = {r["dataset"]: r["coverage_pct"] for r in board["coverage_heat_map"]}
    assert "OHLCV" in heat
    assert "Financials" in heat
    assert any(r["index"] == "NIFTY 50" for r in board["coverage_by_index"])
    assert "companies_completed_today" in board["backfill_throughput"]
    assert any(r["source"] == "NSE" for r in board["source_reliability"])


def test_weekly_audit_builds_repair_queue(monkeypatch):
    from knowledge_factory.historical_depth.coverage_audit import run_coverage_audit, load_repair_queue
    from knowledge_factory.historical_depth.collectors import collect_entity_history
    from knowledge_factory.historical_depth import queue as bf_queue

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY"],
    )
    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.prioritised_universe",
        lambda **kwargs: ["INFY"],
    )
    monkeypatch.setattr(bf_queue, "supported_universe", lambda: ["INFY"])
    # Empty company → many gaps
    report = run_coverage_audit(entities=["INFY"], force=True)
    assert report["skipped"] is False
    assert report["counts"]["repair_queue"] >= 1
    q = load_repair_queue()
    assert len(q["items"]) >= 1

    # Fresh audit skips
    again = run_coverage_audit(entities=["INFY"], force=False)
    assert again.get("skipped") is True

    collect_entity_history("INFY", prefer_live=False)


def test_throughput_recording():
    from continuous_gather_learn.ops_observability import backfill_throughput, record_throughput_sample
    from knowledge_factory.historical_depth import store as hd_store

    record_throughput_sample(companies=3, years=45.0, documents=10, extracts=12)
    t = backfill_throughput()
    assert t["companies_completed_today"] >= 0  # may also come from engine state
    daily = hd_store.get_report("backfill_daily_throughput") or {}
    assert daily
    day = t["day"]
    assert daily[day]["companies"] >= 3
    assert daily[day]["extracts"] >= 12


def test_cgl_production_includes_ops(monkeypatch):
    from continuous_gather_learn.production import dashboard

    monkeypatch.setenv("CONTINUOUS_GATHER_LEARN", "true")
    d = dashboard()
    assert "ops" in d
    assert d["ops"].get("collector_health") is not None or d["ops"].get("error")
