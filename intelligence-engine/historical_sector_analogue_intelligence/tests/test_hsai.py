"""Sprint 11.4 — Historical Sector Analogue Intelligence tests."""

from __future__ import annotations

from historical_sector_analogue_intelligence import traces
from historical_sector_analogue_intelligence.production import (
    analogues,
    analogues_for_sector,
    current_regime,
    dashboard,
    forecast_tip,
    health,
    regime_history,
    run,
    search,
)
from historical_sector_analogue_intelligence.schema import NO_HSAI_ACTIONS, SIMILARITY_DIMENSIONS
from historical_sector_analogue_intelligence.similarity import (
    DIMENSION_WEIGHTS,
    relative_similarity,
    score_dimensions,
)
from historical_sector_analogue_intelligence.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_hsai_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "HSAI"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["phase"] == "11.4"
    for item in NO_HSAI_ACTIONS:
        assert item in h["does_not"]
    assert len(h["similarity_dimensions"]) == len(SIMILARITY_DIMENSIONS)
    assert "Banking" in h["supported_sectors"]


def test_weights_sum_to_one() -> None:
    assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


def test_similarity_deterministic() -> None:
    current = {
        "revenue_growth": 12.5,
        "earnings_growth": 13.0,
        "margin_profile": 3.55,
        "roe": 15.2,
        "valuation": 17.0,
        "relative_performance": 3.0,
        "interest_rate": 6.25,
        "inflation": 3.9,
        "currency": 84.0,
        "policy": 6.5,
        "industry_structure": 7.5,
    }
    hist_same = dict(current)
    hist_2013 = {
        "revenue_growth": 10.0,
        "earnings_growth": 4.0,
        "margin_profile": 3.0,
        "roe": 13.5,
        "valuation": 15.5,
        "relative_performance": -8.0,
        "interest_rate": 7.75,
        "inflation": 9.5,
        "currency": 68.0,
        "policy": 5.0,
        "industry_structure": 6.5,
    }
    s1, _, m1, _ = score_dimensions(current, hist_same)
    s2, _, _, _ = score_dimensions(current, hist_same)
    assert s1 == s2 == 100.0
    assert len(m1) == 11
    assert relative_similarity(6.5, 6.5, scale=3.0) == 100.0

    s2013, details, matching, non_matching = score_dimensions(current, hist_2013)
    assert 0 < s2013 < 100
    assert details
    assert non_matching
    assert score_dimensions(current, hist_2013)[0] == s2013


def test_run_publishes_ranked_analogues() -> None:
    summary = run(enrich_hsip=False, enrich_cskp=False)
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] >= 20
    assert "Banking" in summary["sectors"]

    pack = analogues(sector="Banking")
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


def test_banking_current_closest_to_2025_not_2008() -> None:
    run(sector="Banking", enrich_hsip=False, enrich_cskp=False)
    pack = analogues(sector="Banking", limit=10)
    by_period = {a["matched_period"]: a["similarity_score"] for a in pack["analogues"]}
    assert "2025" in by_period
    assert "2008" in by_period
    assert by_period["2025"] > by_period["2008"]
    top = pack["analogues"][0]
    assert top["matched_period"] in {"2025", "2017", "2022"}
    assert top["confidence"] in {"High", "Medium", "Low"}


def test_search_it_2022_question() -> None:
    out = search(
        question="Which historical period most resembles the current IT sector in 2022?",
        top_k=5,
    )
    assert out["providers_queried"] == []
    assert out["collected_on_request"] is False
    assert out["sector"] == "IT Services"
    assert out["query"]["target_period"] == "2022"
    assert out["n"] >= 1
    assert out["analogues"][0]["matched_period"] == "2022"
    ana = out["analogues"][0]
    assert ana["key_differences"]
    assert ana["historical_outcome"]
    assert ana["equity_outcome"]


def test_regime_apis_and_sector_surface() -> None:
    cur = current_regime(sector="Capital Goods")
    assert cur["providers_queried"] == []
    assert cur["sector"] == "Capital Goods"
    assert cur["regime"]["features"]["revenue_growth"] is not None

    hist = regime_history(sector="Auto")
    assert hist["n"] >= 5
    assert any(r["period"] == "2020" for r in hist["regimes"])

    run(sector="Pharma", enrich_hsip=False, enrich_cskp=False)
    pharma = analogues_for_sector("Pharma")
    assert pharma["sector"] == "Pharma"
    assert pharma["n"] >= 1


def test_forecast_tip_no_providers() -> None:
    tip = forecast_tip(sector="FMCG", top_k=3)
    assert tip["providers_queried"] == []
    assert tip["collected_on_request"] is False
    assert tip["gateway"] == "HSAI_KRIG"
    assert tip["feeds_sprint"] == "11.5"
    assert tip["sector"] == "FMCG"
    assert tip["n"] >= 1
    assert tip["top_analogues"][0]["similarity_score"] >= 0
    assert tip["top_analogues"][0]["explainability"]
    assert tip["top_analogues"][0]["historical_outcome_bundle"]


def test_dashboard_and_traces() -> None:
    run(enrich_hsip=False, enrich_cskp=False)
    board = dashboard()
    assert board["board"] == "Historical Sector Analogue"
    assert board["principles"]["deterministic_similarity"] is True
    assert board["current_sector_regime"]
    assert board["top_analogue_matches"]
    assert board["similarity_distribution"]
    assert board["confidence_distribution"]
    assert board["historical_coverage"]
    assert board["analogue_freshness"]
    assert board["coverage_by_sector"]
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    assert "sector_analogue_search" in names or "sector_analogue_search" in all_names
    assert "sector_similarity_scoring" in all_names
    assert "sector_analogue_ranking" in all_names
    assert "sector_analogue_refresh" in all_names


def test_no_analogue_without_explainability() -> None:
    out = search(sector="Banking", top_k=3)
    for ana in out["analogues"]:
        assert ana["explainability"]["method"] == "weighted_relative_distance"
        assert ana["dimension_scores"]
        contrib = ana["explainability"]["dimension_contributions"]
        assert len(contrib) >= 6
