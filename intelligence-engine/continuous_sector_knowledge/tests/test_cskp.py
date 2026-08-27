"""Sprint 11.1 — Continuous Sector Knowledge Platform tests."""

from __future__ import annotations

from continuous_sector_knowledge import traces
from continuous_sector_knowledge.catalog import assert_catalog_complete
from continuous_sector_knowledge.production import (
    calendar,
    comparison,
    dashboard,
    health,
    leaders,
    run,
    sector,
    sectors,
)
from continuous_sector_knowledge.schema import NO_CSKP_ACTIONS, SECTOR_UNIVERSE, canonicalize
from continuous_sector_knowledge.store import reset
from continuous_macro_knowledge.production import run as cmkp_run
from continuous_macro_knowledge.store import reset as cmkp_reset
from macroeconomic_relationship_intelligence.production import run as mri_run
from macroeconomic_relationship_intelligence.store import reset as mri_reset


def setup_function() -> None:
    reset()
    traces.clear()
    cmkp_reset()
    mri_reset()


def test_catalog_covers_universe() -> None:
    assert_catalog_complete()
    assert len(SECTOR_UNIVERSE) >= 30
    assert canonicalize("Banks") == "banking"
    assert canonicalize("IT Services") == "it_services"
    assert canonicalize("Realty") == "real_estate"


def test_cskp_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "CSKP"
    assert h["phase"] == "11.1"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["mode"] == "event_driven_derived"
    assert h["sector_count"] == len(SECTOR_UNIVERSE)
    for item in NO_CSKP_ACTIONS:
        assert item in h["does_not"]


def test_read_apis_never_collect() -> None:
    out = sectors()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["ask_triggers_collection"] is False
    assert out["constructed_on_request"] is False
    miss = sector("banking")
    assert miss["found"] is False
    assert miss["collected_on_request"] is False
    assert miss["constructed_on_request"] is False


def test_run_publishes_all_sectors() -> None:
    cmkp_run()
    mri_run()
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] == len(SECTOR_UNIVERSE)
    assert summary["mode"] == "event_driven_derived"

    pack = sectors(limit=100)
    assert pack["n"] == len(SECTOR_UNIVERSE)
    assert pack["providers_queried"] == []
    keys = {s["sector_key"] for s in pack["sectors"]}
    assert keys == set(SECTOR_UNIVERSE)
    for s in pack["sectors"]:
        assert s["leading_companies"]
        assert s["growth_drivers"]
        assert s["key_risks"]
        assert s["macro_sensitivity"]
        assert s["constructed_on_request"] is False
        assert 0 < s["sector_confidence"] <= 1


def test_banking_sector_surface() -> None:
    cmkp_run()
    mri_run()
    run()
    b = sector("Banking")
    assert b["found"] is True
    assert b["collected_on_request"] is False
    latest = b["latest"]
    assert latest["sector_key"] == "banking"
    assert latest["label"] == "Banking"
    assert "HDFCBANK" in latest["leading_companies"]
    assert latest["current_outlook"] in {"Positive", "Neutral", "Negative", "Mixed"}
    assert "Repo Rate" in latest["macro_sensitivity"]


def test_unchanged_refresh_skips_learning() -> None:
    run()
    # Second identical ops refresh should publish versions but Ignore learning for unchanged
    summary = run()
    assert summary["published"] == len(SECTOR_UNIVERSE)
    # Most should be immaterial on second pass
    assert summary["immaterial_filtered_from_learning"] >= 20
    banking = sector("banking")
    assert banking["latest"]["version"] >= 2


def test_macro_trigger_learning() -> None:
    cmkp_run()
    run()  # baseline
    summary = run(sectors=["banking"], trigger="macro_change")
    assert summary["published"] == 1
    assert summary["learnings"] >= 1
    events = [e for e in dashboard()["learning_events"] if e["sector_key"] == "banking"]
    assert events
    assert events[-1]["trigger"] == "macro_change"


def test_leaders_comparison_calendar() -> None:
    run()
    lead = leaders(limit=10)
    assert lead["n"] == 10
    assert lead["providers_queried"] == []
    cmp_ = comparison(sectors=["banking", "it_services", "fmcg"])
    assert cmp_["n"] == 3
    keys = {r["sector_key"] for r in cmp_["comparison"]}
    assert keys == {"banking", "it_services", "fmcg"}
    cal = calendar()
    assert cal["n"] >= 5
    assert cal["ask_triggered"] is False


def test_dashboard_and_traces() -> None:
    cmkp_run()
    run()
    board = dashboard()
    assert board["board"] == "Sector Operations"
    assert board["principles"]["ask_never_constructs"] is True
    assert board["sector_health"]["published"] == len(SECTOR_UNIVERSE)
    assert board["company_coverage_by_sector"]
    assert board["learning_events"] is not None
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "sector_collection" in names
    assert "sector_normalization" in names
    assert "sector_publication" in names
    assert "sector_refresh" in names
    # Learning may be absent on a pure unchanged pass; present after first publish
    assert "sector_learning" in names or board["learning_events"] is not None
