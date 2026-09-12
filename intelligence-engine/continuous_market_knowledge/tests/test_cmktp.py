"""Sprint 12.1 — Continuous Market Knowledge Platform tests."""

from __future__ import annotations

from continuous_market_knowledge import traces
from continuous_market_knowledge.catalog import assert_catalog_complete
from continuous_market_knowledge.production import (
    breadth,
    dashboard,
    flows,
    health,
    leadership,
    liquidity,
    market,
    market_health,
    markets,
    regime,
    run,
    volatility,
)
from continuous_market_knowledge.schema import MARKET_UNIVERSE, NO_CMKTP_ACTIONS, canonicalize
from continuous_market_knowledge.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_catalog_covers_universe() -> None:
    assert_catalog_complete()
    assert len(MARKET_UNIVERSE) >= 10
    assert canonicalize("NIFTY") == "india_equity"
    assert canonicalize("FII") == "institutional_flows"
    assert canonicalize("breadth") == "breadth"


def test_cmktp_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "CMKTP"
    assert h["phase"] == "12.1"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["mode"] == "event_driven_derived"
    assert h["not_a_market_data_service"] is True
    assert h["domain_count"] == len(MARKET_UNIVERSE)
    for item in NO_CMKTP_ACTIONS:
        assert item in h["does_not"]


def test_read_apis_never_collect() -> None:
    out = markets()
    assert out["n"] == 0
    assert out["collected_on_request"] is False
    assert out["ask_triggers_collection"] is False
    assert out["constructed_on_request"] is False
    miss = market()
    assert miss["found"] is False
    assert miss["collected_on_request"] is False
    assert miss["constructed_on_request"] is False


def test_run_publishes_all_domains() -> None:
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] == len(MARKET_UNIVERSE)
    assert summary["mode"] == "event_driven_derived"

    pack = markets(limit=100)
    assert pack["n"] == len(MARKET_UNIVERSE)
    assert pack["providers_queried"] == []
    keys = {d["domain_key"] for d in pack["domains"]}
    assert keys == set(MARKET_UNIVERSE)
    for d in pack["domains"]:
        assert d["market_regime"]
        assert d["constructed_on_request"] is False
        assert 0 < d["confidence"] <= 1


def test_composite_market_and_domain_surfaces() -> None:
    run()
    comp = market()
    assert comp["found"] is True
    assert comp["collected_on_request"] is False
    m = comp["market"]
    assert m["market_regime"]
    assert m["breadth"] is not None
    assert m["liquidity"] is not None
    assert m["leadership"] is not None
    assert m["health_score"] is not None
    assert m["risk_sentiment"]

    r = regime()
    assert r["found"] is True
    assert r["market_regime"]
    assert r["providers_queried"] == []

    b = breadth()
    assert b["found"] is True
    assert b["breadth"]
    assert "participation_pct" in b["breadth"] or "advance_decline_ratio" in b["breadth"]

    assert liquidity()["found"] is True
    assert leadership()["found"] is True
    assert flows()["found"] is True
    assert volatility()["found"] is True
    h = market_health()
    assert h["found"] is True
    assert h["health_score"] is not None


def test_unchanged_refresh_skips_learning() -> None:
    run()
    summary = run()
    assert summary["published"] == len(MARKET_UNIVERSE)
    assert summary["immaterial_filtered_from_learning"] >= 7


def test_material_trigger_learning() -> None:
    run()
    summary = run(domains=["breadth"], trigger="breadth_surge")
    assert summary["published"] == 1
    assert summary["learnings"] >= 1


def test_dashboard_and_traces() -> None:
    run()
    board = dashboard()
    assert board["board"] == "Market Intelligence Operations"
    assert board["principles"]["not_a_market_data_service"] is True
    assert board["principles"]["higher_order_concepts_internal"] is True
    assert board["current_market_regime"]
    assert board["market_health_score"] is not None
    assert board["breadth_dashboard"] is not None
    assert board["sector_leadership"] is not None
    assert board["risk_sentiment"]
    assert board["knowledge_freshness"]
    assert board["collection_status"]
    assert board["publication_status"]
    all_names = {t["name"] for t in traces.recent(200)}
    for required in (
        "market_collection",
        "market_validation",
        "market_normalization",
        "market_materiality",
        "market_publication",
        "market_retrieval",
    ):
        assert required in all_names


def test_internal_health_formula() -> None:
    run()
    h = market_health()
    tip_health = h.get("market_health") or {}
    assert tip_health.get("formula") or h.get("health_score")
    assert float(h["health_score"]) > 0
