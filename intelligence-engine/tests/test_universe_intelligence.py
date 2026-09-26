"""AGIB v1.2 — Institutional Universe Intelligence acceptance suite.

Institutional acceptance criteria (not only engineering tests):
  - Universe is a registry, not a list
  - Point-in-time membership is queryable
  - Only Level 7 + all gates PASS = Institutional Coverage
  - ICI is the operational north-star metric
  - Incremental updates rebuild only changed companies
  - Provenance on registry objects
  - Cross-universe support declared
  - Phases 1–7 / KF / IDQ remain frozen (soft-wire only)
"""

from __future__ import annotations

from knowledge_factory.store import repository as kf_store
from universe_intelligence import store as iui_store
from universe_intelligence.company_registry import compile_company, get_company
from universe_intelligence.coverage_levels import coverage_level_for
from universe_intelligence.coverage_score import coverage_score
from universe_intelligence.dashboard import universe_health
from universe_intelligence.ici import institutional_coverage_index
from universe_intelligence.incremental import apply_incremental, detect_changes
from universe_intelligence.membership import memberships_for_company, members_as_of, was_member
from universe_intelligence.pipeline import run_universe_intelligence_pipeline
from universe_intelligence.production import health, quality_gates_summary
from universe_intelligence.quality_gates import institutional_quality_gates
from universe_intelligence.registry import list_universes, universe_tree
from universe_intelligence.schema import (
    FREEZE_LOCKS,
    INSTITUTIONAL_COVERAGE_LEVEL,
    ICI_WEIGHTS,
    IUI_VERSION,
)


def setup_function() -> None:
    kf_store.reset_store()
    iui_store.reset_store()
    try:
        from knowledge_factory.historical_depth import store as hd_store

        hd_store.reset_store()
    except Exception:
        pass
    try:
        from knowledge_factory.macro_intelligence import store as imi_store

        imi_store.reset_store()
    except Exception:
        pass


def test_freeze_locks_and_health():
    h = health()
    assert h["version"] == IUI_VERSION
    assert h["not_a_reasoning_engine"] is True
    assert h["freeze_locks"]["phases_1_7"] is True
    assert h["freeze_locks"]["knowledge_factory_architecture"] is True
    assert h["freeze_locks"]["decision_quality"] is True
    assert h["freeze_locks"]["never_fabricate"] is True
    assert FREEZE_LOCKS["no_raw_api_to_frameworks"] is True


def test_universe_registry_not_a_list():
    board = list_universes()
    assert board["n"] >= 6
    ids = {u["universe_id"] for u in board["universes"]}
    assert "NIFTY_50" in ids
    assert "NIFTY_100" in ids
    assert "NIFTY_500" in ids
    assert "SPX" in ids  # cross-universe declared
    assert "NDX" in ids
    # Declared global must not silently claim active institutional coverage
    spx = next(u for u in board["universes"] if u["universe_id"] == "SPX")
    assert spx["status"] == "declared"
    tree = universe_tree()
    assert "NIFTY_500" in (tree.get("children") or {}) or "NIFTY_100" in tree.get("by_id", {})


def test_point_in_time_membership():
    # ZOMATO joined Nifty 100 in fixture 2021-08-01
    before = was_member(ticker="ZOMATO", universe_id="NIFTY_100", as_of="2020-01-01")
    after = was_member(ticker="ZOMATO", universe_id="NIFTY_100", as_of="2022-01-01")
    assert before["member"] is False
    assert after["member"] is True
    assert after["fabricated"] is False

    # YESBANK historical leave window
    during = was_member(ticker="YESBANK", universe_id="NIFTY_50", as_of="2015-06-01")
    after_leave = was_member(ticker="YESBANK", universe_id="NIFTY_50", as_of="2021-01-01")
    assert during["member"] is True
    assert after_leave["member"] is False

    # INFY relationships queryable
    rel = memberships_for_company("INFY")
    ids = {m["universe_id"] for m in rel["memberships"]}
    assert "NIFTY_50" in ids
    assert "NIFTY_100" in ids
    assert "NIFTY_500" in ids
    assert "NIFTY_IT" in ids

    pit = members_as_of("NIFTY_100", "2022-12-31")
    assert pit["n"] > 0
    assert "ZOMATO" in pit["members"]


def test_coverage_levels_only_7_is_institutional():
    run_universe_intelligence_pipeline(universe_id="NIFTY_500", force_full=True)
    lvl = coverage_level_for("INFY")
    assert lvl["coverage_level"] == INSTITUTIONAL_COVERAGE_LEVEL
    assert lvl["institutional_coverage"] is True
    assert lvl["coverage_level_name"] == "decision_ready"

    unknown = coverage_level_for("NOT_A_REAL_TICKER_ZZZ")
    assert unknown["coverage_level"] < INSTITUTIONAL_COVERAGE_LEVEL
    assert unknown["institutional_coverage"] is False


def test_quality_gates_one_failure_means_no_coverage():
    run_universe_intelligence_pipeline(universe_id="NIFTY_100", force_full=True)
    gates = institutional_quality_gates("INFY")
    assert gates["institutional_ready"] is True
    assert all(v == "PASS" for v in gates["gates"].values())
    assert gates["rule"].startswith("One FAIL")

    bad = institutional_quality_gates("NOT_A_REAL_TICKER_ZZZ")
    assert bad["institutional_ready"] is False
    assert bad["institutional_coverage"] is False
    assert any(v == "FAIL" for v in bad["gates"].values())


def test_coverage_score_and_ici():
    run_universe_intelligence_pipeline(universe_id="NIFTY_100", force_full=True)
    score = coverage_score("INFY")
    assert score["coverage_score"] >= 90.0
    assert "identity" in score["components"]
    assert "evidence" in score["components"]

    ici = institutional_coverage_index("INFY")
    assert abs(sum(ICI_WEIGHTS.values()) - 1.0) < 1e-9
    assert ici["ici"] >= 90.0
    assert ici["band"] in {"institutional", "strong", "adequate"}
    assert set(ici["components"]) == set(ICI_WEIGHTS)


def test_provenance_on_company_registry():
    run_universe_intelligence_pipeline(universe_id="NIFTY_50", force_full=True)
    co = get_company("INFY", refresh=True)["company"]
    assert co["fabricated"] is False
    assert "provenance" in co
    prov = co["provenance"]
    for f in ("source", "retrieved_at", "validated_at", "confidence", "collector", "derived_from"):
        assert f in prov
    assert "identity" in co
    assert "value" in co["identity"] and "provenance" in co["identity"]


def test_incremental_updates_not_full_rebuild():
    # First run primes fingerprints
    run_universe_intelligence_pipeline(universe_id="NIFTY_50", force_full=True)
    # Second detect should show mostly unchanged
    cs = detect_changes("NIFTY_50")
    assert cs["n_members"] == 50
    assert len(cs["unchanged"]) >= 40
    # Incremental apply with no real KF drift rebuilds only stale/missing/changed
    result = apply_incremental("NIFTY_50", force_full=False, ensure_kf=False)
    assert result["mode"] == "incremental"
    assert result["fabricated"] is False


def test_universe_health_ops_heartbeat():
    run_universe_intelligence_pipeline(universe_id="NIFTY_500", force_full=True)
    health_board = universe_health(universe_id="NIFTY_500", ensure=False)
    assert health_board["title"] == "AGIB Universe Health"
    assert health_board["north_star"]["name"] == "Institutional Coverage Index"
    assert health_board["coverage"]["members"] == 500
    assert health_board["coverage"]["institutional_coverage"] == 500
    assert health_board["coverage"]["institutional_coverage_pct"] == 100.0
    assert health_board["coverage"]["avg_ici"] >= 90.0
    assert health_board["failure_count"] == 0
    assert health_board["missing_count"] == 0
    assert health_board["validation_failures"] == 0

    qg = quality_gates_summary("NIFTY_500")
    assert qg["passed"] is True
    assert qg["institutional_ready"] == 500


def test_institutional_acceptance_infosys_class_sample():
    """Institutional acceptance: Infosys-class depth across Tier-2 sample."""
    run_universe_intelligence_pipeline(universe_id="NIFTY_500", force_full=True)
    for t in ("INFY", "BEL", "HIKAL", "COFORGE"):
        co = compile_company(t)
        assert co["institutional_coverage"] is True, (t, co.get("quality_gates"))
        assert co["coverage_level"] == 7
        assert co["ici"] >= 90.0
        assert co["fabricated"] is False
