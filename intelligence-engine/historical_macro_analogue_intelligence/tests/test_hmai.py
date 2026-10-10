"""Sprint 10.4 — Historical Macro Analogue Intelligence tests."""

from __future__ import annotations

from historical_macro_analogue_intelligence import traces
from historical_macro_analogue_intelligence.production import (
    analogues,
    analogues_for_country,
    current_regime,
    dashboard,
    forecast_tip,
    health,
    regime_history,
    run,
    search,
)
from historical_macro_analogue_intelligence.schema import NO_HMAI_ACTIONS
from historical_macro_analogue_intelligence.similarity import (
    DIMENSION_WEIGHTS,
    relative_similarity,
    score_dimensions,
)
from historical_macro_analogue_intelligence.store import reset
from continuous_macro_knowledge.production import run as cmkp_run
from continuous_macro_knowledge.store import reset as cmkp_reset
from historical_macro_intelligence.production import run as hmip_run
from historical_macro_intelligence.store import reset as hmip_reset
from macroeconomic_relationship_intelligence.production import run as mri_run
from macroeconomic_relationship_intelligence.store import reset as mri_reset


def setup_function() -> None:
    reset()
    traces.clear()
    cmkp_reset()
    hmip_reset()
    mri_reset()


def test_hmai_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "HMAI"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["phase"] == "10.4"
    for item in NO_HMAI_ACTIONS:
        assert item in h["does_not"]
    assert len(h["similarity_dimensions"]) == 9


def test_weights_sum_to_one() -> None:
    assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


def test_similarity_deterministic() -> None:
    current = {
        "interest_rate": 6.5,
        "inflation": 3.7,
        "gdp": 7.4,
        "liquidity": 1.2,
        "fiscal": 5.1,
        "currency": 83.5,
        "bond_yield": 6.9,
        "global_growth": 3.2,
        "commodity": 2.1,
    }
    hist_2025 = dict(current)
    hist_2013 = {
        "interest_rate": 7.75,
        "inflation": 9.5,
        "gdp": 5.5,
        "liquidity": -0.5,
        "fiscal": 4.5,
        "currency": 68.0,
        "bond_yield": 8.5,
        "global_growth": 3.4,
        "commodity": 6.0,
    }
    s1, d1, m1, _ = score_dimensions(current, hist_2025)
    s2, d2, m2, _ = score_dimensions(current, hist_2025)
    assert s1 == s2 == 100.0
    assert len(m1) == 9
    assert relative_similarity(6.5, 6.5, scale=3.0) == 100.0

    s2013, details, matching, non_matching = score_dimensions(current, hist_2013)
    assert 0 < s2013 < 100
    assert details
    assert all(d.score >= 0 for d in details)
    assert non_matching  # inflation etc. should diverge
    # Re-run identical → identical score
    assert score_dimensions(current, hist_2013)[0] == s2013


def test_run_publishes_ranked_analogues() -> None:
    cmkp_run()
    hmip_run()
    mri_run()
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert summary["published"] >= 4
    assert summary["top_similarity"] is not None
    assert summary["top_similarity"] >= 55

    pack = analogues()
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
        assert ana["matching_dimensions"] or ana["non_matching_dimensions"]


def test_current_closest_to_2025_not_2013() -> None:
    cmkp_run()
    hmip_run()
    run()
    pack = analogues(limit=10)
    by_period = {a["matched_period"]: a["similarity_score"] for a in pack["analogues"]}
    assert "2025" in by_period
    assert "2013" in by_period
    assert by_period["2025"] > by_period["2013"]
    # Top match should be recent disinflation window or 2018 late-cycle — not GFC/COVID
    top = pack["analogues"][0]
    assert top["matched_period"] in {"2025", "2018"}
    assert top["confidence"] in {"High", "Medium", "Low"}


def test_search_2013_question() -> None:
    cmkp_run()
    hmip_run()
    out = search(question="How similar is today's macro environment to 2013?", top_k=5)
    assert out["providers_queried"] == []
    assert out["collected_on_request"] is False
    assert out["query"]["target_period"] == "2013"
    assert out["n"] >= 1
    assert out["analogues"][0]["matched_period"] == "2013"
    ana = out["analogues"][0]
    assert "Inflation" in " ".join(ana["non_matching_dimensions"] + ana["matching_dimensions"])
    assert ana["key_differences"]
    assert ana["historical_outcome"]
    assert ana["equity_outcome"]


def test_regime_apis() -> None:
    cmkp_run()
    cur = current_regime()
    assert cur["providers_queried"] == []
    assert cur["regime"]["features"]["interest_rate"] is not None
    hist = regime_history()
    assert hist["n"] >= 5
    assert any(r["period"] == "2022" for r in hist["regimes"])


def test_country_surface() -> None:
    cmkp_run()
    hmip_run()
    run()
    india = analogues_for_country("India")
    assert india["country"] == "India"
    assert india["n"] >= 1


def test_forecast_tip_no_providers() -> None:
    cmkp_run()
    hmip_run()
    mri_run()
    tip = forecast_tip(top_k=3)
    assert tip["providers_queried"] == []
    assert tip["collected_on_request"] is False
    assert tip["gateway"] == "HMAI_KRIG"
    assert tip["feeds_sprint"] == "10.5"
    assert tip["n"] >= 1
    assert tip["top_analogues"][0]["similarity_score"] >= 0
    assert tip["top_analogues"][0]["explainability"]


def test_dashboard_and_traces() -> None:
    cmkp_run()
    hmip_run()
    run()
    board = dashboard()
    assert board["board"] == "Historical Macro Analogue"
    assert board["principles"]["deterministic_similarity"] is True
    assert board["current_macro_regime"]
    assert board["top_analogue_matches"]
    assert board["similarity_distribution"]
    assert board["historical_coverage"]
    assert board["analogue_freshness"]
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "macro_analogue_search" in names
    assert "macro_similarity_scoring" in names
    assert "macro_analogue_ranking" in names


def test_no_analogue_without_explainability() -> None:
    cmkp_run()
    out = search(top_k=3)
    for ana in out["analogues"]:
        assert ana["explainability"]["method"] == "weighted_relative_distance"
        assert ana["dimension_scores"]
        contrib = ana["explainability"]["dimension_contributions"]
        assert len(contrib) >= 5
