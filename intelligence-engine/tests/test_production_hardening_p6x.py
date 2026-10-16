"""Production Hardening — unit tests with injected packs / small universes."""

from __future__ import annotations

from production_hardening.data_quality import run_data_quality
from production_hardening.performance import run_performance_profile
from production_hardening.production import health, run_hardening_suite
from production_hardening.regression import capture_company_snapshot, run_gold_regression
from production_hardening.scale import run_scale_test
from production_hardening.schema import ENGINE_CODE, GOLD_REGRESSION_UNIVERSE, VERSION
from production_hardening.universe import load_nifty500_symbols, resolve_universe


def _pack(ticker: str, score: float = 60.0) -> dict:
    entity = "TMPV" if ticker == "TATAMOTORS" else ticker
    return {
        "ok": True,
        "entity": entity,
        "display": ticker,
        "memory": {
            "ok": True,
            "entity": entity,
            "memory_version": 2,
            "compiled_at": "2026-07-28T12:00:00+00:00",
            "confidence": 0.8,
            "sector_history": {"sector_key": "it_services" if ticker == "TCS" else "banks"},
            "financial_history": {"available": True, "revenue": {"yoy": 10}},
        },
        "memory_delta": {"status": "UNCHANGED", "n_field_changes": 0, "summary": "noop"},
        "knowledge_graph": {
            "n_nodes": 4,
            "n_edges": 5,
            "peers": ["INFY"] if ticker == "TCS" else ["ICICIBANK"],
            "themes": ["AI"] if ticker == "TCS" else [],
            "sector_key": "it_services" if ticker == "TCS" else "banks",
        },
        "opportunity": {
            "ok": True,
            "entity": entity,
            "display": ticker,
            "score": score,
            "confidence": 70.0,
            "research_priority": "Medium" if score >= 50 else "Low",
            "why_now": f"{ticker} stable research context",
            "blockers": [],
            "catalysts": [
                {"name": "Quarterly results", "importance": "High", "expected_window": "near_term"}
            ],
            "dimensions": {"valuation": {"score": 55}, "financial_momentum": {"score": 60}},
            "freshness": {"memory_version": 2, "as_of": "2026-07-28T12:00:00+00:00", "memory_compiled_at": "2026-07-28T12:00:00+00:00"},
            "opportunity": {"knowledge_delta": {"status": "UNCHANGED", "n_field_changes": 0}},
            "provenance": {"raw_apis_queried": False},
        },
    }


def test_health():
    h = health()
    assert h["engine"] == ENGINE_CODE
    assert h["version"] == VERSION
    assert h["not_an_intelligence_engine"] is True
    assert h["issues_recommendations"] is False
    assert list(GOLD_REGRESSION_UNIVERSE) == h["gold_universe"]


def test_universe_nifty500_and_presets():
    smoke = resolve_universe(preset="smoke")
    assert smoke["n"] == 10
    assert "TCS" in smoke["symbols"]
    gold = resolve_universe(preset="gold")
    assert gold["n"] == 5
    assert "TCS" in gold["symbols"]
    sample = resolve_universe(preset="sample_100")
    assert sample["n"] == 100
    syms = load_nifty500_symbols(limit=25)
    assert len(syms) == 25


def test_gold_regression_deterministic_with_inject(tmp_path, monkeypatch):
    monkeypatch.setenv("AGIB_HARDENING_RESULTS_DIR", str(tmp_path))
    packs = {t: _pack(t, score=60 + i) for i, t in enumerate(GOLD_REGRESSION_UNIVERSE)}
    # Update baseline
    r1 = run_gold_regression(update_baseline=True, injected_by_ticker=packs)
    assert r1["status"] == "baseline_updated"
    # Verify stable
    r2 = run_gold_regression(update_baseline=False, injected_by_ticker=packs)
    assert r2["status"] == "pass"
    assert r2["mismatches"] == []
    # Fingerprint stable
    a = capture_company_snapshot("TCS", company_pack=packs["TCS"])
    b = capture_company_snapshot("TCS", company_pack=packs["TCS"])
    assert a["fingerprint"] == b["fingerprint"]


def test_gold_regression_detects_drift(tmp_path, monkeypatch):
    monkeypatch.setenv("AGIB_HARDENING_RESULTS_DIR", str(tmp_path))
    packs = {t: _pack(t, score=50.0) for t in GOLD_REGRESSION_UNIVERSE}
    run_gold_regression(update_baseline=True, injected_by_ticker=packs)
    drifted = {**packs, "TCS": _pack("TCS", score=90.0)}
    r = run_gold_regression(update_baseline=False, injected_by_ticker=drifted)
    assert r["status"] == "fail"
    assert any(m["ticker"] == "TCS" for m in r["mismatches"])


def test_scale_smoke_with_custom_worker():
    calls = []

    def worker(t: str):
        calls.append(t)
        return {"ok": True, "entity": t}

    out = run_scale_test(symbols=["TCS", "INFY", "HAL"], worker=worker, mode="custom")
    assert out["n"] == 3
    assert out["ok_n"] == 3
    assert out["throughput_per_min"] is not None
    assert out["latency_ms"]["p50"] is not None
    assert len(calls) == 3


def test_data_quality_injected():
    packs = {t: _pack(t) for t in ("TCS", "HDFCBANK")}
    dq = run_data_quality(universe=["TCS", "HDFCBANK"], injected_by_ticker=packs)
    assert dq["n"] == 2
    assert dq["cache_hit_rate_pct"] == 100.0
    assert dq["sla_pass_n"] == 2


def test_performance_profile_injected():
    # Injected packs still exercise graph/oie/replay/research paths for missing pieces;
    # ensure function returns structure.
    packs = {"TCS": _pack("TCS")}
    perf = run_performance_profile(tickers=["TCS"], injected_by_ticker=packs)
    assert perf["n"] == 1
    assert "avg_ms" in perf
    assert perf["profiles"][0]["ticker"] == "TCS"


def test_hardening_suite_smoke_structure(monkeypatch):
    # Keep suite fast: stub scale + gold + dq + perf
    from production_hardening import production as prod

    monkeypatch.setattr(
        prod,
        "run_gold_regression",
        lambda **k: {"status": "pass", "passed": True, "mismatches": [], "ok_n": 5, "universe": list(GOLD_REGRESSION_UNIVERSE)},
    )
    monkeypatch.setattr(
        prod,
        "run_data_quality",
        lambda **k: {"sla_pass_n": 5, "n": 5, "cache_hit_rate_pct": 80.0, "failures": [], "freshness": {}},
    )
    monkeypatch.setattr(
        prod,
        "run_performance_profile",
        lambda **k: {"avg_ms": {"total": 12.0}, "profiles": []},
    )
    monkeypatch.setattr(
        prod,
        "run_scale_test",
        lambda **k: {
            "n": 10,
            "ok_n": 10,
            "throughput_per_min": 100.0,
            "latency_ms": {"p50": 5},
            "memory": {"rss_mb_delta": 1},
            "success_rate_pct": 100,
            "fail_n": 0,
            "errors": [],
        },
    )
    monkeypatch.setattr(
        prod,
        "build_observability_board",
        lambda **k: {"health": "ok"},
    )
    out = run_hardening_suite(scale_preset="smoke")
    assert out["observability_health"] == "ok"
    assert out["scale"]["n"] == 10
    assert out["issues_recommendations"] is False
