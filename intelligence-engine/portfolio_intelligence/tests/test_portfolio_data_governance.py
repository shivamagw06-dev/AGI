from __future__ import annotations

from institutional_warehouse import store
from portfolio_intelligence.portfolio import packs
from portfolio_intelligence.risk_budget.score import empirical_risk_budget


def test_portfolio_warehouse_tabs_are_immutable_entity_ledgers():
    for tab_id in (
        "portfolio_snapshots", "portfolio_holdings", "portfolio_daily_returns", "portfolio_attribution",
    ):
        tab = store.get_tab(tab_id)
        assert tab.mode == "append"
        assert tab.entity_column == "portfolio_id"


def test_seed_portfolio_is_explicitly_not_production_data(monkeypatch):
    monkeypatch.setattr(packs, "_warehouse_portfolio", lambda _portfolio_id: None)
    result = packs.portfolio_for("agib_core_india")
    assert result["data_lineage"]["source"] == "seed_research_pack"
    assert result["data_lineage"]["empirical_risk_ready"] is False
    assert result["data_lineage"]["attribution_ready"] is False


def test_warehouse_portfolio_requires_complete_dated_holdings(monkeypatch):
    rows = {
        "portfolio_snapshots": [{"portfolio_id": "live", "as_of": "2026-08-14", "status": "ACTIVE"}],
        "portfolio_holdings": [{"portfolio_id": "live", "as_of": "2026-08-14", "ticker": "ABC", "weight": 0.8}],
        "portfolio_daily_returns": [{"portfolio_id": "live", "date": f"d{i}", "return_pct": 0.1} for i in range(252)],
        "portfolio_attribution": [{"portfolio_id": "live", "date": "2026-08-14", "ticker": "ABC"}],
    }
    monkeypatch.setattr(store, "all_rows", lambda tab, **_kwargs: rows[tab])
    result = packs._warehouse_portfolio("live")
    assert result["data_lineage"]["source"] == "institutional_warehouse"
    assert result["data_lineage"]["weights_valid"] is True
    assert result["data_lineage"]["empirical_risk_ready"] is True
    assert result["data_lineage"]["attribution_ready"] is True


def test_empirical_risk_uses_realized_returns_and_benchmark():
    rows = [
        {"return_pct": 0.1 if i % 2 else -0.05, "benchmark_return_pct": 0.08 if i % 2 else -0.04}
        for i in range(252)
    ]
    result = empirical_risk_budget(rows, max_drawdown=0.20)
    assert result["method"] == "empirical_daily_returns_v1"
    assert result["observations"] == 252
    assert result["expected_volatility"] is not None
    assert result["beta_to_benchmark"] is not None


def test_empirical_risk_rejects_short_history():
    assert empirical_risk_budget([{"return_pct": 0.1}] * 62, max_drawdown=0.20) is None
