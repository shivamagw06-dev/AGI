from __future__ import annotations

from hedge_fund_lab.backtests import momentum_backtest
from hedge_fund_lab.calculators import pair_diagnostics


def _price_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for day in range(420):
        label = f"2025-{day:04d}"
        for symbol, multiplier in (("WIN", 1.003), ("MID", 1.001), ("LOSE", 0.999)):
            rows.append({"date": label, "symbol": symbol, "adjusted_close": 100 * multiplier ** day,
                         "volume": 100_000})
    return rows


def test_momentum_backtest_is_point_in_time_and_costed():
    result = momentum_backtest(
        _price_rows(),
        classifications={"WIN": "A", "MID": "B", "LOSE": "C"},
        config={"holdings": 1, "min_average_daily_value": 1, "one_way_cost_bps": 25, "portfolio_capital": 100_000},
    )
    assert result["ok"] is True
    assert result["execution"]["signal_time"] == "prior_close"
    assert result["coverage"]["rebalance_count"] > 0
    assert result["rebalances"][0]["selected"] == ["WIN"]
    assert result["metrics"]["cumulative_return_pct"] is not None
    validation = result["validation"]
    assert validation["status"] == "COMPLETED"
    assert validation["lookahead_check"] is True
    assert validation["costs_included"] is True
    assert validation["periods"]["train"]["end"] < validation["periods"]["validation"]["start"]
    assert validation["periods"]["validation"]["end"] < validation["periods"]["test"]["start"]
    assert validation["out_of_sample_observations"] >= 21
    assert result["capacity"]["status"] == "COMPLETED"
    assert result["capacity"]["passes_assumed_capital"] is True
    assert result["capacity"]["minimum_estimated_capacity"] >= 100_000


def test_momentum_backtest_fails_closed_without_history():
    result = momentum_backtest(_price_rows()[:20], config={"min_average_daily_value": 1})
    assert result["ok"] is False
    assert result["error"] == "insufficient_price_history"


def test_pair_diagnostics_never_claims_cointegration_without_test():
    long_prices = [100 + index * 0.2 + (index % 7) * 0.03 for index in range(150)]
    short_prices = [90 + index * 0.18 for index in range(150)]
    result = pair_diagnostics(long_prices, short_prices)
    assert result["ok"] is True
    assert result["adf_status"] == "not_estimated_without_statistical_test_dependency"
