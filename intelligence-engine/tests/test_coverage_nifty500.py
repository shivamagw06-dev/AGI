"""Track 1 — Nifty 500 Institutional Decision Coverage (Infosys-class depth)."""

from __future__ import annotations

from knowledge_factory.coverage import (
    NIFTY_100,
    NIFTY_500,
    TARGET_20,
    coverage_dimensions,
    daily_health_scorecard,
    decision_coverage,
    entity_coverage,
    morning_coverage_dashboard,
)
from knowledge_factory.institutional_depth import (
    REFERENCE_ENTITY,
    acceptance_for_company,
    institutional_decision_coverage,
    institutional_depth_checklist,
)
from knowledge_factory.production import run_daily_pipeline
from knowledge_factory.store import repository as store
from institutional_reasoning.fundamentals.primitives import covered_entities, has_primitives
from institutional_reasoning.fundamentals.market_series import monthly_returns
from institutional_reasoning.fundamentals.universe import NIFTY_50, tier_report, universe_tiers


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


def test_nifty_500_declared_size():
    assert len(NIFTY_500) == 500
    assert set(NIFTY_100).issubset(set(NIFTY_500))
    assert set(NIFTY_50).issubset(set(NIFTY_500))


def test_nifty_500_primitives_and_risk_series():
    for e in NIFTY_500:
        assert has_primitives(e), e
        assert monthly_returns(e), e
    assert set(NIFTY_500).issubset(set(covered_entities()))
    assert len(covered_entities()) >= 500


def test_universe_tiers_discipline():
    board = universe_tiers()
    assert board["discipline"] == "tier_quality_before_breadth"
    t1 = board["tiers"]["tier_1_nifty_100"]
    t2 = board["tiers"]["tier_2_nifty_500"]
    assert t1["declared"] == 100
    assert t1["by_level"]["full"] == 100
    assert t1["status"] == "complete"
    assert t2["declared"] == 500
    assert t2["by_level"]["full"] == 500
    assert board["tiers"]["tier_3_midcap_thematic"]["status"] == "deferred"
    assert board["tiers"]["tier_4_global"]["status"] == "deferred"
    report = tier_report("nifty_500")
    assert report["declared"] == 500
    assert report["by_level"]["uncovered"] == 0


def test_nifty_500_decision_coverage_100():
    run_daily_pipeline(entities=list(NIFTY_500))
    dc = decision_coverage(NIFTY_500)
    assert dc["decision_ready"] == 500, dc["gaps"][:20]
    assert dc["decision_coverage_pct"] == 100.0
    assert dc["universe"] == "nifty_500"
    assert entity_coverage(NIFTY_500)["ready"] == 500


def test_institutional_decision_coverage_infosys_class():
    run_daily_pipeline(entities=list(NIFTY_500))
    # Reference standard itself is Infosys-class.
    ref = institutional_depth_checklist(REFERENCE_ENTITY)
    assert ref["institutional_depth_ready"], (ref["missing"], ref["insufficient"])

    idc = institutional_decision_coverage(NIFTY_500)
    assert idc["north_star"] == "institutional_decision_coverage"
    assert idc["n"] == 500
    assert idc["institutional_depth_ready"] == 500, idc["gaps"][:20]
    assert idc["institutional_decision_coverage_pct"] == 100.0
    assert idc["decision_ready"] == 500


def test_onboarding_acceptance_tests_sample():
    """Eight acceptance tests for newly onboarded Tier-2 names."""
    run_daily_pipeline(entities=list(NIFTY_500))
    tier2 = [e for e in NIFTY_500 if e not in set(NIFTY_100)]
    samples = [e for e in ("HIKAL", "ANURAS", "NOCIL", "COFORGE", "MPHASIS") if e in NIFTY_500] or tier2[:5]
    for e in samples:
        result = acceptance_for_company(e)
        assert result["accepted"], (e, result["tests"], result["depth"]["missing"])
        assert result["fabricated"] is False
        assert result["passed"] == 8


def test_transparent_insufficiency_never_fabricates():
    depth = institutional_depth_checklist("NOT_A_REAL_TICKER_ZZZ")
    assert depth["fabricated"] is False
    assert depth["institutional_depth_ready"] is False
    assert depth["missing"]
    acc = acceptance_for_company("NOT_A_REAL_TICKER_ZZZ")
    assert acc["tests"]["transparent_insufficiency"] is True
    assert acc["fabricated"] is False


def test_daily_health_and_morning_board_nifty_500():
    run_daily_pipeline(entities=list(NIFTY_500))
    health = daily_health_scorecard(ensure_pipeline=False)
    assert health["title"] == "AGIB Daily Health"
    assert health["decision_coverage"]["nifty_100"] == 100.0
    assert health["decision_coverage"]["nifty_500"] == 100.0
    assert health["decision_coverage"]["institutional_decision_coverage"] == 100.0
    assert health["north_star"]["universe"] == "nifty_500"
    assert health["north_star"]["ready"] == 500
    assert health["validation_failures"] == 0
    assert health["universe_tiers"]["tiers"]["tier_2_nifty_500"]["by_level"]["full"] == 500

    board = morning_coverage_dashboard()
    assert board["north_star"]["universe"] == "nifty_500"
    assert board["north_star"]["ready"] == 500
    assert board["tiers"]["nifty_500"]["covered"] == 500
    assert board["tiers"]["nifty_500"]["institutional_depth_ready"] == 500
    assert board["kpi"] == "institutional_decision_coverage_pct"
    dims = coverage_dimensions(NIFTY_500)
    assert dims["decision_coverage"]["coverage_pct"] == 100.0


def test_prior_universes_remain_green():
    run_daily_pipeline(entities=list(dict.fromkeys([*TARGET_20, *NIFTY_500])))
    assert decision_coverage(TARGET_20)["decision_coverage_pct"] == 100.0
    assert decision_coverage(NIFTY_50)["decision_coverage_pct"] == 100.0
    assert decision_coverage(NIFTY_100)["decision_coverage_pct"] == 100.0
