"""Sprint 3 — Nifty 100 Decision Coverage must hit 100/100."""

from __future__ import annotations

from knowledge_factory.coverage import (
    NIFTY_100,
    TARGET_20,
    confidence_coverage,
    coverage_dimensions,
    daily_health_scorecard,
    decision_coverage,
    entity_coverage,
    evidence_coverage,
    morning_coverage_dashboard,
)
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


def test_nifty_100_declared_size():
    assert len(NIFTY_100) == 100
    assert set(NIFTY_50).issubset(set(NIFTY_100))


def test_nifty_100_primitives_and_risk_series():
    for e in NIFTY_100:
        assert has_primitives(e), e
        assert monthly_returns(e), e
    assert set(NIFTY_100).issubset(set(covered_entities()))


def test_nifty_100_decision_coverage_100():
    run_daily_pipeline(entities=list(NIFTY_100))
    dc = decision_coverage(NIFTY_100)
    assert dc["decision_ready"] == 100, dc["gaps"]
    assert dc["decision_coverage_pct"] == 100.0
    assert dc["universe"] == "nifty_100"
    for row in dc["rows"]:
        assert row["decision_ready"], (row["entity"], row["missing"])


def test_four_coverage_dimensions():
    run_daily_pipeline(entities=list(NIFTY_100))
    dims = coverage_dimensions(NIFTY_100)
    assert dims["entity_coverage"]["coverage_pct"] == 100.0
    assert dims["decision_coverage"]["coverage_pct"] == 100.0
    evid = evidence_coverage(NIFTY_100)
    assert evid["by_field"]["historical_pe"]["coverage_pct"] == 100.0
    assert evid["by_field"]["roic"]["coverage_pct"] == 100.0
    assert evid["by_field"]["risk"]["coverage_pct"] == 100.0
    conf = confidence_coverage(NIFTY_100)
    assert conf["threshold"] == 90.0
    assert conf["coverage_pct"] >= 0.0
    assert entity_coverage(NIFTY_100)["ready"] == 100


def test_daily_health_scorecard():
    run_daily_pipeline(entities=list(dict.fromkeys([*TARGET_20, *NIFTY_100])))
    health = daily_health_scorecard(ensure_pipeline=False)
    assert health["title"] == "AGIB Daily Health"
    assert health["decision_coverage"]["nifty_100"] == 100.0
    assert health["decision_coverage"]["nifty_50"] == 100.0
    assert health["decision_coverage"]["target_20"] == 100.0
    # Track 1 may report full Nifty 500 once Tier-2 panels are loaded.
    assert health["decision_coverage"]["nifty_500"] in {20.0, 100.0}
    assert health["decision_coverage"]["global"] == 0.0
    assert health["validation_failures"] == 0
    assert health["roadmap_next"] in {
        "historical_depth",
        "sector_intelligence",
        "macro_intelligence",
        "nifty_500",
        "tier_3_midcap_thematic",
    }
    assert "entity_coverage" in health["dimensions"]
    assert "confidence_coverage" in health["dimensions"]


def test_morning_board_keeps_nifty_100_tier():
    run_daily_pipeline(entities=list(dict.fromkeys([*TARGET_20, *NIFTY_100])))
    board = morning_coverage_dashboard()
    # Track 1 promotes north star to Nifty 500 Institutional Decision Coverage.
    assert board["north_star"]["universe"] in {"nifty_100", "nifty_500"}
    assert board["tiers"]["nifty_100"]["covered"] == 100
    assert board["tiers"]["nifty_50"]["covered"] == 50
    assert board["tiers"]["target_20"]["covered"] == 20
    assert board["kpi"] in {"decision_coverage_pct", "institutional_decision_coverage_pct"}
    assert board["daily_health"]["decision_coverage"]["nifty_100"] == 100.0


def test_universe_tier_report_nifty_100_full():
    report = tier_report("nifty_100")
    assert report["declared"] == 100
    assert report["by_level"]["full"] == 100
    assert report["by_level"]["uncovered"] == 0
