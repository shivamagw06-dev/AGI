"""Sprint 12.4 — Historical Market Analogue Intelligence (HMKAI) tests."""

from __future__ import annotations

from historical_market_analogue_intelligence import traces
from historical_market_analogue_intelligence.production import (
    analogues,
    analogues_for_market,
    current_regime,
    dashboard,
    forecast_tip,
    health,
    regime_history,
    report,
    run,
    search,
)
from historical_market_analogue_intelligence.schema import NO_HMKAI_ACTIONS, SIMILARITY_DIMENSIONS
from historical_market_analogue_intelligence.similarity import (
    DIMENSION_WEIGHTS,
    relative_similarity,
    score_dimensions,
)
from historical_market_analogue_intelligence.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_hmkai_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "HMKAI"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["phase"] == "12.4"
    for item in NO_HMKAI_ACTIONS:
        assert item in h["does_not"]
    assert len(h["similarity_dimensions"]) == len(SIMILARITY_DIMENSIONS)
    assert "India" in h["supported_markets"]


def test_weights_sum_to_one() -> None:
    assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


def test_similarity_deterministic() -> None:
    current = {
        "market_regime": 5.2,
        "breadth": 58.0,
        "liquidity": 64.0,
        "volatility": 45.0,
        "fii_flows": 56.0,
        "dii_flows": 68.0,
        "leadership": 63.0,
        "bond_yields": 6.85,
        "usd_index": 103.5,
        "interest_rate": 6.25,
        "inflation": 3.9,
    }
    hist_same = dict(current)
    hist_2008 = {
        "market_regime": 1.0,
        "breadth": 18.0,
        "liquidity": 25.0,
        "volatility": 90.0,
        "fii_flows": 15.0,
        "dii_flows": 35.0,
        "leadership": 20.0,
        "bond_yields": 8.5,
        "usd_index": 85.0,
        "interest_rate": 9.0,
        "inflation": 8.3,
    }
    s1, _, m1, _ = score_dimensions(current, hist_same)
    s2, _, _, _ = score_dimensions(current, hist_same)
    assert s1 == s2 == 100.0
    assert len(m1) == 11
    assert relative_similarity(6.5, 6.5, scale=3.0) == 100.0

    s2008, details, matching, non_matching = score_dimensions(current, hist_2008)
    assert 0 < s2008 < 100
    assert details
    assert non_matching
    assert score_dimensions(current, hist_2008)[0] == s2008


def test_run_publishes_ranked_analogues() -> None:
    summary = run(enrich_hmkip=False, enrich_cmktp=False)
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] >= 8
    assert "India" in summary["markets"]

    pack = analogues(market="India")
    assert pack["providers_queried"] == []
    assert pack["collected_on_request"] is False
    assert pack["n"] >= 4
    for ana in pack["analogues"]:
        assert ana["similarity_score"] >= 0
        assert ana["dimension_scores"]
        assert ana["supporting_evidence"]
        assert ana["similarity_explainable"] is True
        assert ana["providers_queried"] == []
        assert ana["explainability"]["deterministic"] is True
        assert ana["historical_outcome"]
        assert ana["historical_outcome_bundle"]
        assert ana["version"] >= 1


def test_india_current_closest_to_2025_not_2008() -> None:
    run(market="India", enrich_hmkip=False, enrich_cmktp=False)
    pack = analogues(market="India", limit=10)
    by_period = {a["matched_period"]: a["similarity_score"] for a in pack["analogues"]}
    assert "2025" in by_period
    assert "2008" in by_period
    assert by_period["2025"] > by_period["2008"]
    top = pack["analogues"][0]
    assert top["matched_period"] in {"2025", "2021", "2022", "2016"}
    assert top["confidence"] in {"High", "Medium", "Low"}


def test_search_covid_and_correction_questions() -> None:
    out = search(
        question="Is the current correction similar to 2020 COVID Crash in India?",
        top_k=5,
    )
    assert out["providers_queried"] == []
    assert out["collected_on_request"] is False
    assert out["market"] == "India"
    assert out["query"]["target_period"] == "2020"
    assert out["n"] >= 1
    assert out["analogues"][0]["matched_period"] == "2020"
    ana = out["analogues"][0]
    assert ana["key_differences"]
    assert ana["historical_outcome"]
    assert ana["equity_outcome"]
    assert ana["historical_outcome_bundle"]["return_90d"]


def test_regime_apis_and_report() -> None:
    cur = current_regime(market="India")
    assert cur["providers_queried"] == []
    assert cur["market"] == "India"
    assert cur["regime"]["features"]["breadth"] is not None

    hist = regime_history(market="India")
    assert hist["n"] >= 8
    assert any(r["period"] == "2020" for r in hist["regimes"])

    run(market="Global", enrich_hmkip=False, enrich_cmktp=False)
    global_pack = analogues_for_market("Global")
    assert global_pack["market"] == "Global"
    assert global_pack["n"] >= 1

    rep = report(market="India", top_k=3)
    assert rep["gateway"] == "HMKAI_KRIG"
    assert rep["n"] >= 1
    assert rep["feeds_sprint"] == "12.5"


def test_forecast_tip_no_providers() -> None:
    tip = forecast_tip(market="India", top_k=3)
    assert tip["providers_queried"] == []
    assert tip["collected_on_request"] is False
    assert tip["gateway"] == "HMKAI_KRIG"
    assert tip["feeds_sprint"] == "12.5"
    assert tip["market"] == "India"
    assert tip["n"] >= 1
    assert tip["top_analogues"][0]["similarity_score"] >= 0
    assert tip["top_analogues"][0]["explainability"]
    assert tip["top_analogues"][0]["historical_outcome_bundle"]


def test_dashboard_and_traces() -> None:
    run(enrich_hmkip=False, enrich_cmktp=False)
    board = dashboard()
    assert board["board"] == "Historical Market Analogue"
    assert board["programme_short"] == "HMKAI"
    assert board["principles"]["deterministic_similarity"] is True
    assert board["current_market_regime"]
    assert board["top_analogue_matches"]
    assert board["similarity_distribution"]
    assert board["confidence_distribution"]
    assert board["historical_coverage"]
    assert board["analogue_freshness"]
    assert board["coverage_by_market"]
    assert board["phase"] == "12.4"
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    assert "market_analogue_search" in names or "market_analogue_search" in all_names
    assert "market_similarity_scoring" in all_names
    assert "market_analogue_ranking" in all_names
    assert "market_analogue_refresh" in all_names


def test_no_analogue_without_explainability() -> None:
    out = search(market="India", top_k=3)
    for ana in out["analogues"]:
        assert ana["explainability"]["method"] == "weighted_relative_distance"
        assert ana["dimension_scores"]
        contrib = ana["explainability"]["dimension_contributions"]
        assert len(contrib) >= 6
