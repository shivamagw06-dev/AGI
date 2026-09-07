"""Sprint 2 — Nifty 50 Decision Coverage must hit 50/50."""

from __future__ import annotations

from knowledge_factory.coverage import TARGET_20, decision_coverage, morning_coverage_dashboard
from knowledge_factory.production import run_daily_pipeline
from knowledge_factory.store import repository as store
from institutional_reasoning.fundamentals.primitives import covered_entities, has_primitives
from institutional_reasoning.fundamentals.market_series import monthly_returns
from institutional_reasoning.fundamentals.universe import NIFTY_50, tier_report


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


def test_nifty_50_primitives_and_risk_series():
    assert len(NIFTY_50) == 50
    for e in NIFTY_50:
        assert has_primitives(e), e
        assert monthly_returns(e), e
    assert set(NIFTY_50).issubset(set(covered_entities()))


def test_nifty_50_decision_coverage_100():
    run_daily_pipeline(entities=list(NIFTY_50))
    dc = decision_coverage(NIFTY_50)
    assert dc["decision_ready"] == 50, dc["gaps"]
    assert dc["decision_coverage_pct"] == 100.0
    assert dc["universe"] == "nifty_50"
    for row in dc["rows"]:
        assert row["decision_ready"], (row["entity"], row["missing"])


def test_target_20_still_complete():
    run_daily_pipeline(entities=list(TARGET_20))
    dc = decision_coverage(TARGET_20)
    assert dc["decision_ready"] == 20
    assert dc["decision_coverage_pct"] == 100.0


def test_morning_board_keeps_nifty_50_complete():
    # Sprint 3: north star is Nifty 100; Nifty 50 remains a complete tier.
    from knowledge_factory.coverage import NIFTY_100, TARGET_20

    run_daily_pipeline(entities=list(dict.fromkeys([*TARGET_20, *NIFTY_100])))
    board = morning_coverage_dashboard()
    assert board["tiers"]["nifty_50"]["covered"] == 50
    assert board["tiers"]["nifty_50"]["coverage_pct"] == 100.0
    assert board["tiers"]["target_20"]["covered"] == 20
    assert board["evidence_packs"] >= 50
    assert board["kpi"] in {"decision_coverage_pct", "institutional_decision_coverage_pct"}
    assert board["tiers"]["nifty_100"]["covered"] == 100


def test_universe_tier_report_full():
    report = tier_report("nifty_50")
    assert report["covered"] == 50
    assert report["by_level"]["full"] == 50
    assert report["by_level"]["uncovered"] == 0
