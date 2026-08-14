from portfolio_intelligence import production


def test_unknown_strategy_fails_closed():
    result = production.strategy_execution_gate("does_not_exist")
    assert result["execution_eligible"] is False
    assert result["decision"] == "BLOCKED"


def test_unvalidated_strategy_cannot_reach_portfolio(monkeypatch):
    monkeypatch.setattr("strategy_lab.registry_store.load_latest_evidence", lambda force=True: {})
    result = production.strategy_execution_gate("cross_sectional_momentum")
    assert result["execution_eligible"] is False
    assert result["decision"] == "BLOCKED"
    assert result["supported_lifecycle"] == "EXPERIMENTAL"
