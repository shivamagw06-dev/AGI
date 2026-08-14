from __future__ import annotations

from institutional_reliability import production


def test_roadmap_fails_closed_when_phase_evidence_is_missing(monkeypatch):
    monkeypatch.setattr("strategy_lab.registry_store.load_latest_evidence", lambda force=False: {})
    monkeypatch.setattr("forecast_intelligence_engine.calibration_board", lambda: {
        "status": "ACCUMULATING_OUTCOMES", "execution_eligible": False,
    })
    monkeypatch.setattr("portfolio_intelligence.production.quality_gates", lambda: {
        "passed": True, "checks": {"enabled": True},
    })
    monkeypatch.setattr("portfolio_intelligence.production.strategy_execution_gate", lambda key: {
        "strategy_id": key, "execution_eligible": False, "decision": "BLOCKED",
    })

    result = production.roadmap_status()

    assert result["status"] == "IN_PROGRESS"
    assert result["execution_eligible"] is False
    assert result["accepted_phases"] == 0
    assert result["phases"]["phase_1_data_integrity"]["accepted"] is False
    assert result["phases"]["phase_4_portfolio_intelligence"]["status"] == "GOVERNED_BLOCKED"


def test_roadmap_cannot_accept_portfolio_phase_without_eligible_strategy(monkeypatch):
    monkeypatch.setattr("strategy_lab.registry_store.load_latest_evidence", lambda force=False: {})
    monkeypatch.setattr("forecast_intelligence_engine.calibration_board", lambda: {
        "status": "RESEARCH_CALIBRATED", "execution_eligible": False,
    })
    monkeypatch.setattr("portfolio_intelligence.production.quality_gates", lambda: {"passed": True})
    monkeypatch.setattr("portfolio_intelligence.production.strategy_execution_gate", lambda key: {
        "strategy_id": key, "execution_eligible": False,
    })

    result = production.roadmap_status()

    assert result["phases"]["phase_3_forecast_intelligence"]["accepted"] is True
    assert result["phases"]["phase_4_portfolio_intelligence"]["accepted"] is False
    assert result["execution_eligible"] is False
