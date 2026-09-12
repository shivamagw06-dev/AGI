"""Sprint 11.5 — Sector Forecast Intelligence tests."""

from __future__ import annotations

from sector_forecast_intelligence import traces
from sector_forecast_intelligence.production import (
    dashboard,
    forecast,
    forecast_all,
    health,
    history,
    probability,
    report,
    run,
    scenarios,
)
from sector_forecast_intelligence.schema import NO_SFI_ACTIONS, SUPPORTED_SECTORS
from sector_forecast_intelligence.store import reset


def setup_function() -> None:
    reset()
    traces.clear()


def test_sfi_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "SFI"
    assert h["phase"] == "11.5"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["predicts_single_path"] is False
    assert h["inherits_macro_from"] == "MFI"
    for item in NO_SFI_ACTIONS:
        assert item in h["does_not"]
    assert "Banking" in h["supported_sectors"]


def test_run_publishes_bbb_report() -> None:
    summary = run(sector="Capital Goods")
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert set(summary["scenarios"]) == {"Bull", "Base", "Bear"}
    assert "Capital Goods" in summary["sectors"]
    dist = summary["per_sector"]["Capital Goods"]["probability_distribution"]
    assert sum(dist.values()) == 100
    assert dist["Base"] >= dist["Bull"]
    assert dist["Bull"] >= 5 and dist["Bear"] >= 5


def test_sector_forecast_evidence_linked() -> None:
    run(sector="Banking")
    out = forecast(sector="Banking")
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
        assert sc["historical_analogues"] is not None
        assert sc["company_impacts"]
        assert sc["revenue_growth"] is not None
        assert sc["earnings_growth"] is not None
        assert sc["margin_outlook"] is not None
        assert sc["valuation_outlook"] is not None
        assert sc["expected_relative_performance"] is not None
    by = {s["scenario"]: s for s in out["scenarios"]}
    assert by["Bull"]["revenue_growth"] > by["Bear"]["revenue_growth"]
    assert by["Bull"]["valuation_outlook"] > by["Bear"]["valuation_outlook"]


def test_company_impact_cascade() -> None:
    out = report(sector="Capital Goods", persist=True)
    cm = out["company_impact_matrix"]
    assert "LT" in cm
    assert set(cm["LT"].keys()) == {"Bull", "Base", "Bear"}
    assert cm["LT"]["Bull"] in {"Positive", "Strong Positive"}
    assert cm["LT"]["Bear"] in {"Negative", "Strong Negative"}
    # Scenario-level transmission present
    bull = next(s for s in out["scenarios"] if s["scenario"] == "Bull")
    tickers = {c["ticker"] for c in bull["company_impacts"]}
    assert "LT" in tickers
    assert "SIEMENS" in tickers
    assert any("Order" in " ".join(c.get("transmission") or []) for c in bull["company_impacts"])


def test_probability_api() -> None:
    run(sector="IT Services")
    pack = probability(sector="IT Services")
    assert pack["sum_pct"] == 100
    assert pack["providers_queried"] == []
    assert (pack.get("confidence") or {}).get("overall_pct", 0) >= 40
    assert len(pack["scenario_probabilities"]) == 3


def test_scenarios_and_forecast_all() -> None:
    pack = scenarios(sector="FMCG")
    assert pack["n"] == 3
    assert pack["sector"] == "FMCG"
    assert pack["collected_on_request"] is False

    all_pack = forecast_all()
    assert all_pack["n"] == len(SUPPORTED_SECTORS)
    assert all_pack["predicts_single_path"] is False
    assert all_pack["providers_queried"] == []


def test_forecast_never_calls_providers() -> None:
    out = forecast(sector="Auto")
    assert out["providers_queried"] == []
    assert out["is_recommendation"] is False
    assert out["is_price_prediction"] is False
    assert out["predicts_single_path"] is False
    assert "create_independent_macro_view" in NO_SFI_ACTIONS


def test_macro_inheritance_field_present() -> None:
    out = report(sector="Pharma", persist=True)
    assert "macro_inheritance" in out
    assert out["macro_inheritance"]["gateway"] == "MFI_KRIG"
    # Soft — may or may not have live MFI published; field must exist
    assert "inherited" in out["macro_inheritance"]


def test_dashboard_and_traces() -> None:
    run(sector="Banking")
    board = dashboard()
    assert board["board"] == "Sector Forecast Intelligence"
    assert board["principles"]["no_single_path_prediction"] is True
    assert board["principles"]["inherits_macro_from_mfi"] is True
    assert board["bull_base_bear_scenarios"]
    assert board["probability_distribution"]
    assert board["confidence"]
    assert board["key_catalysts"] is not None
    assert board["major_risks"] is not None
    assert board["company_impact_summaries"] is not None
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    all_names = {t["name"] for t in traces.recent(200)}
    for required in (
        "sector_forecast_bundle",
        "sector_scenario_generation",
        "sector_probability",
        "sector_confidence",
        "sector_company_impact",
        "sector_forecast_validation",
        "sector_forecast_publication",
    ):
        assert required in names or required in all_names


def test_history_versioned() -> None:
    run(sector="Banking")
    run(sector="Banking")
    hist = history(sector="Banking", limit=10)
    assert hist["n"] >= 2
    assert hist["providers_queried"] == []
    versions = [r["version"] for r in hist["reports"]]
    assert versions == sorted(versions, reverse=True)
