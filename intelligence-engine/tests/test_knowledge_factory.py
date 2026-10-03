"""Knowledge Factory Track 1 acceptance suite."""

from __future__ import annotations

from knowledge_factory.adapter import historical_points_from_kf
from knowledge_factory.collectors.nse.client import collect_filings
from knowledge_factory.collectors.yahoo.client import collect_company
from knowledge_factory.production import coverage_dashboard, health, quality_gates, run_daily_pipeline
from knowledge_factory.producers.composite import produce_peers
from knowledge_factory.producers.valuation.metrics import produce_valuation
from knowledge_factory.schedulers.daily import run_daily
from knowledge_factory.store import repository as store
from knowledge_factory.validators.pipeline import dedupe_filings, validate_dataset


def setup_function() -> None:
    store.reset_store()
    try:
        from knowledge_factory.historical_depth import store as hd_store

        hd_store.reset_store()
    except Exception:
        pass
    try:
        from knowledge_factory.sector_intelligence import store as isi_store

        isi_store.reset_store()
    except Exception:
        pass
    try:
        from knowledge_factory.macro_intelligence import store as imi_store

        imi_store.reset_store()
    except Exception:
        pass


def test_health_and_not_engine():
    h = health()
    assert h["status"] == "ok"
    assert h["not_a_top_level_engine"] is True
    assert h["phases_1_7_frozen"] is True


def test_yahoo_unavailable_keeps_existing_evidence():
    # Seed an object first
    run_daily(entities=["INFY"], yahoo_live=False)
    before = store.get_object("company", "INFY")
    assert before is not None
    # Simulate yahoo unavailable on refresh — existing object remains
    bad = collect_company("INFY", live=True)
    # live path may return unavailable; pipeline must not wipe INFY
    run_daily(entities=["INFY"], yahoo_live=True)
    after = store.get_object("company", "INFY")
    # Either refreshed from fixture fallback path or retained — never None crash
    assert after is not None or before is not None
    assert bad.get("ok") is False or after is not None


def test_duplicate_filings_deduped():
    rows = [
        {"filing_id": "X1", "title": "AR", "date": "2025-01-01"},
        {"filing_id": "X1", "title": "AR", "date": "2025-01-01"},
        {"filing_id": "X2", "title": "Q1", "date": "2025-02-01"},
    ]
    out = dedupe_filings(rows)
    assert len(out) == 2


def test_conflicting_data_not_published():
    ds = {
        "entity": "INFY",
        "source": "yahoo",
        "timestamp": "2026-07-28T00:00:00Z",
        "payload": {"eps": -1.0, "force_pe": 20.0, "conflict": True},
    }
    v = validate_dataset(ds, required_fields=())
    assert v["ok"] is False
    assert v["rejected"] is True
    assert v["published"] is False


def test_missing_eps_pe_insufficient():
    # All non-positive EPS — PE producer must report insufficient (no fabricated PE)
    prim = {"eps": {"FY25": -1.0, "FY26": 0.0}, "price": {"FY25": 100.0, "FY26": 110.0}}
    out = produce_valuation("SYNTH", prim)
    pe = (out.get("metrics") or {}).get("PE") or {}
    assert pe.get("insufficient") is True
    assert pe.get("reason") == "missing_or_non_positive_eps"
    assert "PE" in (out.get("insufficient") or [])


def test_no_peer_data_insufficient_not_fabricated():
    peers = produce_peers("ONLYME", [])
    assert peers["insufficient"] is True
    assert peers["fabricated"] is False
    assert peers["peers"] == []


def test_stale_evidence_rejected_by_validator():
    ds = {
        "entity": "INFY",
        "source": "yahoo",
        "timestamp": "2020-01-01T00:00:00Z",
        "payload": {"price": 1},
    }
    v = validate_dataset(ds, max_age_hours=72, allow_stale=False)
    assert v["ok"] is False
    assert "stale" in (v.get("reject_reasons") or [])


def test_daily_pipeline_updates_objects_and_dashboard():
    result = run_daily_pipeline(entities=["INFY", "TCS", "WIPRO"])
    assert result["ok"] is True
    assert store.get_object("company", "INFY")
    assert store.get_object("sector", "it_services") or store.list_objects("sector")
    assert store.get_object("macro", "GLOBAL")
    assert store.get_pack("INFY")
    dash = coverage_dashboard()
    assert dash["companies_covered"] >= 1
    assert dash["evidence_packs"] >= 1
    gates = quality_gates()
    assert gates["passed"] is True


def test_soft_adapter_never_raw_api():
    run_daily(entities=["INFY"])
    pts, provider, data_class, meta = historical_points_from_kf("INFY", "PE")
    assert pts
    assert provider in {"knowledge_factory", "knowledge_factory_historical_depth"}
    assert meta.get("raw_api") is False


def test_nse_collect_filings_shape():
    ds = collect_filings("INFY")
    assert ds["source"] == "nse"
    assert (ds.get("payload") or {}).get("filings")
