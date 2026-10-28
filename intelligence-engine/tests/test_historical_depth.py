"""Sprint 4 — Historical Depth acceptance + PIT integrity."""

from __future__ import annotations

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.dashboard import historical_depth_dashboard
from knowledge_factory.historical_depth.pipeline import run_historical_pipeline
from knowledge_factory.historical_depth.queries import (
    largest_crisis_drawdown,
    pe_above_percentile,
    performance_across_rate_hiking_cycles,
    valuation_during,
)
from knowledge_factory.historical_depth.time_travel import compare_as_of, state_as_of
from knowledge_factory.historical_depth.validators import assert_no_future_leak
from knowledge_factory.adapter import historical_points_from_kf


CORE = ["INFY", "HDFCBANK", "TCS", "RELIANCE", "ICICIBANK"]


def setup_function() -> None:
    hd_store.reset_store()
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


def test_historical_collectors_and_objects_operational():
    report = run_historical_pipeline(entities=CORE)
    assert report["status"] in {"ok", "degraded"}
    assert report["entities"] == len(CORE)
    for e in CORE:
        assert hd_store.get_series("financials_annual", e)
        assert hd_store.get_series("prices", e)
        assert hd_store.get_object("company", e)
        assert hd_store.get_pack(e)
    assert hd_store.get_object("macro", "GLOBAL")
    assert hd_store.get_regimes()


def test_infosys_valuation_during_2008_historical_only():
    run_historical_pipeline(entities=["INFY"])
    out = valuation_during("INFY", 2008)
    assert out["found"] is True
    assert out["source"] == "historical_evidence_only"
    assert out["fabricated"] is False
    assert out["valuation"]
    assert out["point_in_time_integrity"] is True


def test_compare_infosys_2015_vs_2025():
    run_historical_pipeline(entities=["INFY"])
    out = compare_as_of("INFY", "2015-12-31", "2025-12-31")
    assert out["found"] is True
    assert out["states_loaded"] == 2
    assert out["state_a"]["as_of"] == "2015-12-31"
    assert out["state_b"]["as_of"] == "2025-12-31"
    # Distinct historical states
    pe_a = out.get("pe_a")
    pe_b = out.get("pe_b")
    assert pe_a is not None and pe_b is not None
    assert out["point_in_time_integrity"] is True


def test_pe_exceeding_90th_percentile():
    run_historical_pipeline(entities=["INFY"])
    out = pe_above_percentile("INFY", 90.0)
    assert out["found"] is True
    assert out["n"] >= 1
    for row in out["periods"]:
        assert row["percentile"] >= 90.0


def test_largest_crisis_drawdown():
    run_historical_pipeline(entities=["INFY"])
    out = largest_crisis_drawdown("INFY")
    assert out["found"] is True
    assert out["worst_crisis"] is not None
    assert out["worst_crisis"]["max_drawdown_pct"] < 0
    assert len(out["all_crises"]) >= 2


def test_hdfc_across_three_rate_hiking_cycles():
    run_historical_pipeline(entities=["HDFCBANK"])
    out = performance_across_rate_hiking_cycles("HDFCBANK")
    assert out["found"] is True
    assert out["n_cycles"] >= 3
    assert out["macro_comparison"] is True


def test_replay_as_of_2020_03_31_no_future_leak():
    """Point-in-time integrity: 31 Mar 2020 must not see April 2020 earnings."""
    run_historical_pipeline(entities=["INFY"])
    as_of = "2020-03-31"
    state = state_as_of("INFY", as_of)
    assert state["found"] is True
    assert state["point_in_time_integrity"] is True
    assert state["fabricated"] is False

    # FY20 annual available July 2020 — excluded
    assert "FY20" in state["excluded_future_annual"]
    assert "FY20" not in state["periods_loaded"]["annual"]

    # Q4 results available_from 2020-04-20 — excluded
    assert any(p.endswith("Q4") and "FY20" in p for p in state["excluded_future_quarterly"]) or "FY20Q4" in state[
        "excluded_future_quarterly"
    ]

    annual = (hd_store.get_series("financials_annual", "INFY") or {}).get("records") or []
    quarterly = (hd_store.get_series("financials_quarterly", "INFY") or {}).get("records") or []
    prices = (hd_store.get_series("prices", "INFY") or {}).get("records") or []
    from knowledge_factory.historical_depth.store import filter_pit

    pit = filter_pit([*annual, *quarterly, *prices], as_of)
    leak = assert_no_future_leak(pit, as_of)
    assert leak["ok"] is True
    assert leak["leaks"] == []


def test_historical_evidence_unavailable_transparent():
    run_historical_pipeline(entities=["INFY"])
    out = state_as_of("NOTAREALCO", "2020-03-31")
    assert out["found"] is False
    assert out["insufficient"] is True
    assert out["fabricated"] is False
    assert out["reason"] == "historical_evidence_unavailable"

    missing_year = valuation_during("NOTAREALCO", 2008)
    assert missing_year["found"] is False
    assert missing_year["fabricated"] is False


def test_historical_depth_dashboard_kpi():
    run_historical_pipeline(entities=CORE)
    board = historical_depth_dashboard(entities=CORE)
    assert board["north_star"] == "historical_depth_coverage"
    assert board["average_history_years"] >= 10
    assert board["companies_gt_10y"] == len(CORE)
    assert board["companies_gt_15y"] == len(CORE)
    assert board["companies_gt_20y"] == len(CORE)
    assert board["annual_completeness_pct"] == 100.0
    assert board["historical_evidence_quality"] >= 90.0
    assert board["point_in_time_integrity"] is True
    assert board["roadmap_next"] == "sector_intelligence"


def test_soft_adapter_prefers_historical_depth():
    run_historical_pipeline(entities=["INFY"])
    points, provider, data_class, meta = historical_points_from_kf("INFY", "PE")
    assert points
    assert len(points) >= 15
    assert provider == "knowledge_factory_historical_depth"
    assert meta.get("point_in_time_integrity") is True
    assert data_class == "derived"


def test_nifty100_historical_depth_smoke():
    """Exit-gate scale: declared Nifty 100 receives 20y panels."""
    from knowledge_factory.coverage import NIFTY_100

    report = run_historical_pipeline(entities=list(NIFTY_100))
    assert report["entities"] == 100
    board = historical_depth_dashboard(entities=list(NIFTY_100))
    assert board["companies_gt_20y"] == 100
    assert board["companies_gt_20y_pct"] == 100.0
