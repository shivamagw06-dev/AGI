"""Sprint 12.5 — Market Forecast Intelligence (MKFI) tests."""

from __future__ import annotations

from market_forecast_intelligence import traces
from market_forecast_intelligence.production import (
    catalysts,
    dashboard,
    forecast,
    forecast_all,
    health,
    history,
    probability,
    report,
    risks,
    run,
    scenarios,
)
from market_forecast_intelligence.schema import FORECAST_HORIZONS, NO_MKFI_ACTIONS, SUPPORTED_MARKETS
from market_forecast_intelligence.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_mkfi_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["ok"] is True
    assert h["programme_short"] == "MKFI"
    assert h["phase"] == "12.5"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["predicts_single_path"] is False
    assert h["inherits_macro_from"] == "MFI"
    assert h["mkfi_version"] == h["version"]
    for item in NO_MKFI_ACTIONS:
        assert item in h["does_not"]
    assert "India" in h["supported_markets"]
    assert "market_forecast_publication" in h["langsmith_traces"]


def test_run_publishes_bbb_report() -> None:
    summary = run(markets=["India"], horizons=["6 Months"])
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert set(summary["scenarios"]) == {"Bull", "Base", "Bear"}
    assert summary["published"] == 1
    dist = summary["per_report"]["India:6 Months"]["probability_distribution"]
    assert sum(dist.values()) == 100
    assert dist["Base"] >= dist["Bull"]
    assert dist["Bull"] >= 5 and dist["Bear"] >= 5


def test_market_forecast_evidence_linked() -> None:
    run(markets=["India"], horizons=["6 Months"])
    out = forecast(market="India", horizon="6 Months")
    assert out["providers_queried"] == []
    assert out["collected_on_request"] is False
    assert out["predicts_single_path"] is False
    assert out["is_recommendation"] is False
    assert out["is_price_prediction"] is False
    assert len(out["scenarios"]) == 3
    for sc in out["scenarios"]:
        assert sc["narrative"]
        assert sc["drivers"]
        assert sc["supporting_evidence"]
        assert sc["key_assumptions"]
        assert sc["probability_pct"] is not None
        assert sc["confidence_pct"] is not None
        assert sc["historical_analogues"]
        assert sc["supporting_relationships"]
        assert sc["macro_assumptions"]
        assert sc["catalysts"]
        assert sc["risks"]
        assert sc["invalidators"]
        assert sc["sector_leadership"]
        assert sc["cross_asset_outlook"]
    by = {s["scenario"]: s for s in out["scenarios"]}
    assert by["Bull"]["market_direction"] == "Bullish"
    assert by["Bear"]["market_direction"] == "Bearish"
    assert by["Bull"]["breadth"] == "Improving"
    assert by["Bear"]["breadth"] == "Weakening"


def test_probabilities_sum_100() -> None:
    run(markets=["India"], horizons=["3 Months"])
    pack = probability(market="India", horizon="3 Months")
    assert pack["sum_pct"] == 100
    assert pack["providers_queried"] == []
    assert (pack.get("confidence") or {}).get("overall_pct", 0) >= 40
    assert len(pack["scenario_probabilities"]) == 3


def test_horizons_independent() -> None:
    run(markets=["India"], horizons=["1 Month", "12 Months"])
    m1 = forecast(market="India", horizon="1 Month")
    m12 = forecast(market="India", horizon="12 Months")
    assert m1["horizon"] == "1 Month"
    assert m12["horizon"] == "12 Months"
    assert m1["report_id"] != m12["report_id"]


def test_scenarios_catalysts_risks_and_forecast_all() -> None:
    pack = scenarios(market="India", horizon="6 Months")
    assert pack["n"] == 3
    assert pack["market"] == "India"
    assert pack["collected_on_request"] is False

    cats = catalysts(market="India", horizon="6 Months")
    assert cats["n"] >= 1
    assert cats["providers_queried"] == []

    rsk = risks(market="India", horizon="6 Months")
    assert rsk["n"] >= 1
    assert rsk["invalidation_alerts"] is not None

    all_pack = forecast_all(limit=8)
    assert all_pack["n"] >= 1
    assert all_pack["predicts_single_path"] is False
    assert all_pack["providers_queried"] == []
    assert set(SUPPORTED_MARKETS).issubset({"India", "Global"})
    assert "1 Month" in FORECAST_HORIZONS


def test_forecast_never_calls_providers() -> None:
    out = forecast(market="Global", horizon="6 Months")
    assert out["providers_queried"] == []
    assert out["is_recommendation"] is False
    assert out["is_price_prediction"] is False
    assert out["predicts_single_path"] is False
    assert "query_live_market_feeds" in NO_MKFI_ACTIONS


def test_macro_and_sector_inheritance_fields() -> None:
    out = report(market="India", horizon="6 Months", persist=True)
    assert "macro_inheritance" in out
    assert out["macro_inheritance"]["gateway"] == "MFI_KRIG"
    assert "inherited" in out["macro_inheritance"]
    assert "sector_inheritance" in out
    assert out["sector_inheritance"]["gateway"] == "SFI_KRIG"


def test_dashboard_and_traces() -> None:
    run(markets=["India", "Global"], horizons=["6 Months"])
    board = dashboard()
    assert board["board"] == "Market Forecast Intelligence"
    assert board["principles"]["no_single_path_prediction"] is True
    assert board["principles"]["inherits_macro_from_mfi"] is True
    assert board["bull_base_bear_scenarios"]
    assert board["probability_distribution"]
    assert board["confidence"]
    assert board["key_catalysts"] is not None
    assert board["major_risks"] is not None
    assert board["invalidation_alerts"] is not None
    assert board["sector_leadership_forecast"] is not None
    assert "accuracy_tracking" in board
    assert len(board["reports"]) >= 2
    assert "market_forecast_bundle" in board["langsmith_traces"]
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    for required in (
        "market_forecast_bundle",
        "market_scenario_generation",
        "market_probability",
        "market_confidence",
        "market_risk_engine",
        "market_catalyst_engine",
        "market_forecast_validation",
        "market_forecast_publication",
    ):
        assert required in names or required in all_names


def test_history_versioned() -> None:
    run(markets=["India"], horizons=["6 Months"])
    run(markets=["India"], horizons=["6 Months"])
    hist = history(market="India", horizon="6 Months", limit=10)
    assert hist["n"] >= 2
    assert hist["providers_queried"] == []
    versions = [r["version"] for r in hist["reports"]]
    assert versions == sorted(versions, reverse=True)
