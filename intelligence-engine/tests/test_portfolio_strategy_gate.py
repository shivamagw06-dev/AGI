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


def test_portfolio_analysis_without_strategy_is_research_only(monkeypatch):
    monkeypatch.setattr(production, "is_enabled", lambda: True)
    monkeypatch.setattr(production, "analyse_portfolio", lambda *args, **kwargs: {"found": True})

    result = production.analyse("sample", candidate="RADICO")

    assert result["execution_eligible"] is False
    assert result["execution_governance"]["reason"] == "STRATEGY_ID_REQUIRED"
