"""FG-01 — Forecast & Scenario Graph tests (deterministic, no ML/LLM)."""

from __future__ import annotations

from institutional_decision import history as decision_history
from institutional_forecasting.assumptions import banking_preset_assumptions
from institutional_forecasting.diagnostics import validate_scenario
from institutional_forecasting.probability import probability_for, standard_distribution
from institutional_forecasting.production import (
    get_company_scenarios,
    health,
    reset_for_tests,
    run_company_scenarios,
)
from institutional_forecasting.scenario_engine import run_scenario
from institutional_forecasting.schema import FG_WORKSTREAM_ID
from institutional_forecasting.sensitivity import compute_sensitivity
from institutional_graph.production import reset_for_tests as reset_graphs
from institutional_reporting.composer import compose_report
from institutional_reporting.fixtures import get_fixture


def setup_function(_fn=None):
    decision_history.reset_for_tests()
    reset_for_tests()
    reset_graphs()


def test_health():
    h = health()
    assert h["workstream_id"] == FG_WORKSTREAM_ID
    assert h["deterministic_propagation"] is True
    assert h["ml_price_prediction"] is False
    assert h["llm"] is False


def test_probability_explicit():
    dist = standard_distribution()
    assert abs(dist["base"] + dist["bull"] + dist["bear"] - 1.0) < 1e-9
    assert probability_for("bull", dist) == dist["bull"]
    assert probability_for("base") == 0.50


def test_scenario_creation_and_propagation():
    out = run_company_scenarios(
        "AXISBANK",
        scenarios=["bull"],
        include_graph=True,
        include_propagation=True,
    )
    assert out["ok"] is True, out.get("validation_errors")
    assert len(out["scenarios"]) == 1
    s = out["scenarios"][0]
    assert s["assumptions"]
    assert s["probability"] > 0
    assert s["resulting_decision"] in {"BUY", "HOLD", "SELL"}
    assert s["forecast_graph"]["node_count"] >= 1
    assert s["propagated_impacts"] or s["changed_nodes"]
    assert s["diagnostics"]
    assert validate_scenario(
        __import__("institutional_forecasting.scenario", fromlist=["ForecastScenario"]).ForecastScenario(
            scenario_id=s["scenario_id"],
            scenario_name=s["scenario_name"],
            probability=s["probability"],
            assumptions=tuple(
                __import__(
                    "institutional_forecasting.assumptions", fromlist=["ScenarioAssumption"]
                ).ScenarioAssumption.from_dict(a)
                for a in s["assumptions"]
            ),
            changed_nodes=tuple(s.get("changed_nodes") or ()),
            propagated_impacts=tuple(s.get("propagated_impacts") or ()),
            resulting_decision=s["resulting_decision"],
            resulting_confidence=s["resulting_confidence"],
            diagnostics=s["diagnostics"],
        )
    ) == []


def test_sensitivity_scorecard():
    from institutional_graph.production import get_company_graph
    from institutional_graph.production import _GRAPHS

    get_company_graph("AXISBANK", rebuild=True)
    g = _GRAPHS["AXISBANK"]
    sens = compute_sensitivity(g)
    assert sens["scorecard"]
    assert "NIM" in sens["scorecard"] or "ROE" in sens["scorecard"]


def test_multiple_scenarios_comparison():
    out = run_company_scenarios(
        "KOTAKBANK",
        scenarios=["base", "bull", "bear", "stress"],
        include_propagation=True,
    )
    assert out["ok"] is True
    assert len(out["comparison"]) == 4
    probs = [c["probability"] for c in out["comparison"]]
    assert all(p is not None for p in probs)
    # Stress should be more adverse than bull on decision/score path
    by_name = {s["scenario_name"]: s for s in out["scenarios"]}
    assert by_name["bull"]["resulting_score"] >= by_name["stress"]["resulting_score"]


def test_decision_evolution_tracked():
    out = run_company_scenarios("ICICIBANK", scenarios=["bear", "bull"])
    for s in out["scenarios"]:
        assert "base_decision" in s
        assert "reason_changes" in s
        assert "confidence_delta" in s


def test_integration_four_banks_different_outcomes():
    fingerprints = {}
    for ticker in ("AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"):
        decision_history.reset_for_tests()
        reset_for_tests()
        reset_graphs()
        out = run_company_scenarios(
            ticker, scenarios=["base", "bull", "bear"], include_sensitivity=True
        )
        assert out["ok"] is True
        bull = next(s for s in out["scenarios"] if s["scenario_name"] == "bull")
        bear = next(s for s in out["scenarios"] if s["scenario_name"] == "bear")
        fingerprints[ticker] = (
            bull["resulting_decision"],
            bull["resulting_confidence"],
            bear["resulting_decision"],
            bear["resulting_score"],
            round(bull["score_delta"], 3),
        )
        # Deterministic
        out2 = run_company_scenarios(ticker, scenarios=["bull"])
        assert out2["scenarios"][0]["resulting_confidence"] == bull["resulting_confidence"]
        assert out2["scenarios"][0]["resulting_decision"] == bull["resulting_decision"]

    assert len(set(fingerprints.values())) >= 2


def test_report_consumes_forecast_decisions():
    decision_history.reset_for_tests()
    reset_for_tests()
    reset_graphs()
    report = compose_report(get_fixture("AXISBANK"))
    assert report.ok is True
    assert report.diagnostics.get("forecast_scenarios")
    assert report.diagnostics["forecast_scenarios"].get("comparison")
    assert report.to_dict().get("forecast_scenarios") is True


def test_preset_assumptions():
    bull = banking_preset_assumptions("bull")
    assert any(a.node_key == "rbi_rate" for a in bull)
    assert all(a.confidence > 0 for a in bull)


def test_cli_main():
    from institutional_forecasting.__main__ import main

    assert main(["--health"]) == 0
    assert main(["--ticker", "AXISBANK", "--scenario", "bull"]) == 0


def test_get_company_scenarios_api_shape():
    out = get_company_scenarios("HDFCBANK", include_graph=True, include_propagation=True, rebuild=True)
    assert out["ok"] is True
    assert out.get("scenarios")
    assert out.get("comparison")
