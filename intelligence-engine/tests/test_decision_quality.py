"""Sprint 7 — Institutional Decision Quality acceptance tests."""

from __future__ import annotations

from decision_quality import store as idq_store
from decision_quality.dashboard import institutional_decision_quality_dashboard
from decision_quality.hall import classify_decision, search_hall
from decision_quality.metrics.calibration import build_calibration_report
from decision_quality.pipeline import run_decision_quality_pipeline
from decision_quality.production import health, quality_gates
from decision_quality.replay import missing_outcome, replay_decision
from decision_quality.schema import HALL_CATEGORIES, IDQ_VERSION


def setup_function() -> None:
    idq_store.reset_store()


def _prime():
    return run_decision_quality_pipeline(use_fixtures=True)


def test_health_observability_only():
    h = health()
    assert h["status"] == "ok"
    assert h["never_reasons"] is True
    assert h["not_a_reasoning_engine"] is True
    assert h["phases_1_7_frozen"] is True
    assert h["knowledge_factory_frozen"] is True
    assert h["version"] == IDQ_VERSION


def test_replay_previous_recommendation_identical():
    _prime()
    did = "dec_hdfc_2023_increase"
    first = replay_decision(did)
    second = replay_decision(did)
    assert first["found"] is True
    assert first["matches_stored"] is True
    assert first["identical_decision"]["decision_id"] == did
    assert first["identical_decision"] == second["identical_decision"]
    assert first["path"]["question"]
    assert first["path"]["evidence"]
    assert first["path"]["research"]
    assert first["path"]["portfolio"]
    assert first["path"]["outcome"]
    assert first["no_future_leakage"] is True
    assert first["fabricated"] is False


def test_framework_statistics_success_rates():
    _prime()
    fw = idq_store.get_scorecard("framework", "_index")
    assert fw and fw["scorecards"]
    # residual_income used once on HDFC — success
    ri = fw["scorecards"]["residual_income"]
    assert ri["uses"] == 1
    assert ri["success_rate"] == 1.0
    assert ri["success_rate_pct"] == 100.0
    # dcf used on failing decisions — success rate < 1
    dcf = fw["scorecards"]["dcf"]
    assert dcf["uses"] >= 2
    assert dcf["success_rate"] < 1.0
    assert "average_error" in dcf
    assert dcf["fabricated"] is False


def test_confidence_calibration():
    report = _prime()
    cal = idq_store.get_calibration("latest")
    assert cal
    overall = cal["overall"]
    assert overall["n_with_outcome"] >= 5
    assert 0.0 <= overall["expected_confidence"] <= 1.0
    assert 0.0 <= overall["realised_accuracy"] <= 1.0
    assert overall["calibration_error"] >= 0.0
    # Historical confidence vs realised outcomes present per slice
    assert cal["by_sector"]
    assert cal["by_framework"]
    assert cal["by_macro_regime"]
    assert cal["by_company"]
    assert cal["fabricated"] is False
    # Rebuild matches stored
    decisions = idq_store.all_decisions()
    rebuilt = build_calibration_report(decisions)
    assert rebuilt["overall"]["n_with_outcome"] == overall["n_with_outcome"]
    assert report["status"] == "ok"


def test_sector_dashboard_statistics():
    _prime()
    sector = idq_store.get_scorecard("sector", "_index")
    assert sector and sector["n"] >= 3
    banks = sector["scorecards"]["banks"]
    assert banks["decision_count"] >= 1
    assert banks["prediction_accuracy"] == 100.0
    assert "framework_performance" in banks
    it = sector["scorecards"]["it_services"]
    assert it["decision_count"] >= 1
    assert sector["fabricated"] is False


def test_macro_dashboard_statistics():
    _prime()
    macro = idq_store.get_scorecard("macro", "_index")
    assert macro and macro["n"] >= 2
    high_rates = macro["scorecards"]["high_rates"]
    assert high_rates["decision_count"] >= 2
    assert "best_frameworks" in high_rates
    assert "worst_frameworks" in high_rates
    assert "portfolio_outcomes" in high_rates
    assert isinstance(high_rates["average_accuracy"], (int, float))
    assert macro["fabricated"] is False


def test_portfolio_dashboard_statistics():
    _prime()
    port = idq_store.get_scorecard("portfolio", "aggregate")
    assert port
    assert "position_sizing_quality" in port
    assert "sector_allocation" in port
    assert "risk_allocation" in port
    assert "scenario_quality" in port
    assert "drawdown" in port
    assert "portfolio_alpha" in port
    assert "tracking_error" in port
    assert "decision_accuracy" in port
    assert port["n_with_outcome"] >= 5
    assert port["fabricated"] is False


def test_missing_outcome_transparent_insufficiency():
    _prime()
    out = missing_outcome("dec_tcs_open_no_outcome")
    assert out["insufficient"] is True
    assert out["fabricated"] is False
    assert out["reason"] == "outcome_unavailable"
    metrics = out["metrics"]
    assert metrics["insufficient"] is True
    assert "decision_accuracy" not in (metrics.get("metrics") or {}) or metrics["insufficient"]
    # Must not fabricate accuracy
    assert metrics.get("fabricated") is False


def test_hall_of_fame_and_shame():
    _prime()
    hall = idq_store.get_hall()
    assert hall
    assert hall["counts"]["fame"] >= 1
    assert hall["counts"]["shame"] >= 1
    fame_ids = {e["decision_id"] for e in hall["hall_of_fame"]}
    assert "dec_hdfc_2023_increase" in fame_ids or "dec_infy_2022_hold" in fame_ids
    shame_cats = {e["category"] for e in hall["hall_of_shame"]}
    assert shame_cats & {
        "incorrect_missing_evidence",
        "incorrect_framework_selection",
        "incorrect_macro_assumption",
        "incorrect_portfolio_construction",
        "weak",
    }
    # Searchable
    searched = search_hall(hall="fame")
    assert searched["found"] is True
    assert searched["n"] >= 1
    # Classifier categories are from the closed set
    for e in hall["hall_of_fame"] + hall["hall_of_shame"]:
        assert e["category"] in HALL_CATEGORIES


def test_dashboard_and_quality_gates_operational():
    report = _prime()
    dash = institutional_decision_quality_dashboard()
    assert dash["status"] == "operational"
    kpi = dash["kpi"]
    assert kpi["north_star_kpi"] == "institutional_decision_quality"
    assert kpi["coverage"] >= 50
    assert kpi["counts"]["decisions"] >= 7
    assert "Hall of Fame / Hall of Shame" in dash["displays"]
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["checks"]["observability_only"] is True
    assert report["knowledge_factory_untouched"] is True
    assert report["phases_1_7_untouched"] is True


def test_open_decision_not_in_fame_without_outcome():
    _prime()
    d = idq_store.get_decision("dec_tcs_open_no_outcome")
    cls = classify_decision(d)
    assert cls["insufficient"] is True
    assert cls["category"] is None
    assert cls["fabricated"] is False
