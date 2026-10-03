"""Sprint 10.5 — Macroeconomic Forecast Intelligence tests."""

from __future__ import annotations

from macroeconomic_forecast_intelligence import traces
from macroeconomic_forecast_intelligence.production import (
    dashboard,
    forecast,
    global_forecast,
    health,
    india,
    probability,
    report,
    run,
    scenarios,
)
from macroeconomic_forecast_intelligence.schema import NO_MFI_ACTIONS
from macroeconomic_forecast_intelligence.store import reset
from continuous_macro_knowledge.production import run as cmkp_run
from continuous_macro_knowledge.store import reset as cmkp_reset
from historical_macro_intelligence.production import run as hmip_run
from historical_macro_intelligence.store import reset as hmip_reset
from macroeconomic_relationship_intelligence.production import run as mri_run
from macroeconomic_relationship_intelligence.store import reset as mri_reset
from historical_macro_analogue_intelligence.store import reset as hmai_reset


def setup_function() -> None:
    reset()
    traces.clear()
    cmkp_reset()
    hmip_reset()
    mri_reset()
    hmai_reset()


def _seed() -> None:
    cmkp_run()
    hmip_run()
    mri_run()


def test_mfi_health() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["programme_short"] == "MFI"
    assert h["phase"] == "10.5"
    assert h["ask_triggers_collection"] is False
    assert h["providers_queried_always"] == []
    assert h["predicts_single_path"] is False
    for item in NO_MFI_ACTIONS:
        assert item in h["does_not"]


def test_run_publishes_bbb_report() -> None:
    _seed()
    summary = run()
    assert summary["ok"] is True
    assert summary["ask_triggered"] is False
    assert summary["providers_queried"] == []
    assert set(summary["scenarios"]) == {"Bull", "Base", "Bear"}
    dist = summary["probability_distribution"]
    assert sum(dist.values()) == 100
    assert dist["Base"] >= dist["Bull"]
    assert dist["Bull"] >= 5 and dist["Bear"] >= 5


def test_india_forecast_evidence_linked() -> None:
    _seed()
    run()
    out = india()
    assert out["providers_queried"] == []
    assert out["collected_on_request"] is False
    assert out["predicts_single_path"] is False
    assert len(out["scenarios"]) == 3
    for sc in out["scenarios"]:
        assert sc["narrative"]
        assert sc["drivers"]
        assert sc["supporting_evidence"]
        assert sc["probability_pct"] is not None
        assert sc["confidence_pct"] is not None
        assert sc["historical_analogues"] is not None
        assert sc["sector_impacts"]
        assert sc["company_impacts"]
        assert sc["gdp"] is not None
        assert sc["inflation"] is not None
        assert sc["repo_rate"] is not None
    # Bull repo below Bear repo
    by = {s["scenario"]: s for s in out["scenarios"]}
    assert by["Bull"]["repo_rate"] < by["Bear"]["repo_rate"]
    assert by["Bull"]["gdp"] > by["Bear"]["gdp"]


def test_sector_and_company_impact_matrices() -> None:
    _seed()
    out = report(persist=True)
    sm = out["sector_impact_matrix"]
    assert "Banks" in sm
    assert set(sm["Banks"].keys()) == {"Bull", "Base", "Bear"}
    assert sm["Banks"]["Bull"] in {"Positive", "Strong Positive"}
    assert sm["Banks"]["Bear"] in {"Negative", "Strong Negative"}
    cm = out["company_impact_matrix"]
    assert "HDFCBANK" in cm
    assert "INFY" in cm


def test_probability_api() -> None:
    _seed()
    run()
    p = probability()
    assert p["sum_pct"] == 100
    assert set(p["distribution"].keys()) == {"Bull", "Base", "Bear"}
    assert p["providers_queried"] == []
    assert p["confidence"]["overall_pct"] >= 40


def test_scenarios_and_global() -> None:
    _seed()
    sc = scenarios()
    assert sc["n"] == 3
    assert sc["providers_queried"] == []
    g = global_forecast()
    assert g["region"] == "Global"
    assert g["providers_queried"] == []
    assert len(g["scenarios"]) == 3


def test_forecast_never_calls_providers() -> None:
    _seed()
    out = forecast(country="India")
    assert out["providers_queried"] == []
    assert out.get("is_recommendation") is False
    assert out.get("is_price_prediction") is False


def test_dashboard_and_traces() -> None:
    _seed()
    run()
    board = dashboard()
    assert board["board"] == "Macro Forecast Intelligence"
    assert board["principles"]["no_external_providers"] is True
    assert board["bull_base_bear_scenarios"]
    assert board["probability_distribution"]
    assert board["confidence"]
    assert board["sector_impact_matrix"]
    assert board["company_impact_matrix"]
    assert board["key_macro_catalysts"]
    assert board["upcoming_macro_events"]
    assert board["forecast_history"]["n"] >= 1
    names = {t["name"] for t in board["retrieval_performance"]["traces"]}
    assert "macro_forecast_bundle" in names
    assert "macro_scenario_generation" in names
    assert "macro_probability" in names
    assert "macro_confidence" in names
    assert "macro_sector_impact" in names
    assert "macro_company_impact" in names
    assert "macro_forecast_publication" in names


def test_analogues_consumed_when_hmai_available() -> None:
    _seed()
    out = india()
    # At least one scenario should carry analogue tips from HMAI soft tip
    assert any(s.get("historical_analogues") for s in out["scenarios"])
