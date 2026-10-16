from __future__ import annotations

from datetime import date, timedelta

from hedge_fund_lab.backtests import breakout_backtest, mean_reversion_backtest, momentum_backtest, trend_backtest
from hedge_fund_lab.calculators import pair_diagnostics


def _sessions(count: int, start: date = date(2023, 1, 2)) -> list[str]:
    """Consecutive NSE sessions.

    The fixtures used to label days "2025-0001", which is not a date. The
    harness now drops non-trading days, because roughly 18% of
    daily_market_history falls on a weekend carrying a differently scaled
    series, so a backtest fixture has to look like a real calendar.
    """
    out, day = [], start
    while len(out) < count:
        if day.weekday() < 5:
            out.append(day.isoformat())
        day += timedelta(days=1)
    return out


def _price_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sessions = _sessions(420)
    for day, label in enumerate(sessions):
        for symbol, multiplier in (("WIN", 1.003), ("MID", 1.001), ("LOSE", 0.999)):
            rows.append({"date": label, "symbol": symbol, "close": 100 * multiplier ** day,
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


def test_trend_backtest_is_costed_capacity_checked_and_out_of_sample():
    result = trend_backtest(
        _price_rows(),
        classifications={"WIN": "A", "MID": "B", "LOSE": "C"},
        config={"holdings": 1, "min_average_daily_value": 1, "portfolio_capital": 100_000},
    )
    assert result["ok"] is True
    assert result["strategy"] == "trend_following_long_only"
    assert result["execution"]["execution"] == "next_close"
    assert result["parameters"]["fast_window"] == 50
    assert result["parameters"]["slow_window"] == 200
    assert result["validation"]["status"] == "COMPLETED"
    assert result["validation"]["out_of_sample_observations"] >= 21
    assert result["capacity"]["passes_assumed_capital"] is True


def test_breakout_backtest_uses_prior_channel_and_volume():
    result = breakout_backtest(
        _price_rows(),
        classifications={"WIN": "A", "MID": "B", "LOSE": "C"},
        config={"holdings": 1, "min_average_daily_value": 1, "portfolio_capital": 100_000},
    )
    assert result["ok"] is True
    assert result["strategy"] == "volatility_breakout_long_only"
    assert result["parameters"]["entry_window"] == 55
    assert result["parameters"]["exit_window"] == 20
    assert result["execution"]["signal_time"] == "prior_close"
    assert result["execution"]["execution"] == "next_close"
    assert result["validation"]["status"] == "COMPLETED"
    assert result["capacity"]["passes_assumed_capital"] is True


def test_mean_reversion_backtest_requires_dislocation_inside_positive_trend():
    rows = []
    for day, label in enumerate(_sessions(420)):
        for symbol, growth in (("WIN", 1.003), ("MID", 1.002), ("SLOW", 1.001)):
            close = 100 * growth ** day
            if day % 25 == 0:
                close *= 0.78
            rows.append({"date": label, "symbol": symbol, "close": close, "volume": 100_000})
    result = mean_reversion_backtest(
        rows,
        classifications={"WIN": "A", "MID": "B", "SLOW": "C"},
        config={"holdings": 1, "min_average_daily_value": 1, "portfolio_capital": 100_000},
    )
    assert result["ok"] is True
    assert result["strategy"] == "medium_term_mean_reversion_long_only"
    assert result["parameters"]["entry_z"] == 2.0
    assert result["parameters"]["trend_window"] == 200
    assert result["execution"]["execution"] == "next_close"
    assert result["validation"]["status"] == "COMPLETED"
    assert any(row["selected"] for row in result["rebalances"])


def test_pair_diagnostics_never_claims_cointegration_without_test():
    long_prices = [100 + index * 0.2 + (index % 7) * 0.03 for index in range(150)]
    short_prices = [90 + index * 0.18 for index in range(150)]
    result = pair_diagnostics(long_prices, short_prices)
    assert result["ok"] is True
    assert result["adf_status"] == "not_estimated_without_statistical_test_dependency"


def test_weekend_rows_cannot_reach_the_backtest():
    """About 18% of daily_market_history falls on a day NSE is closed, carrying
    a differently scaled series - MWL printed a tenth of its weekday price every
    Sunday for months before its split. Left in, each weekend fabricates a -90%
    session followed by a +900% one, which is what produced a 17.9% win rate."""
    from hedge_fund_lab.backtests import _clean_prices

    rows = []
    for day, label in enumerate(_sessions(30)):
        rows.append({"date": label, "symbol": "AAA", "close": 100.0, "volume": 100_000})
    rows.append({"date": "2023-01-08", "symbol": "AAA", "close": 10.0, "volume": 100_000})

    cleaned = _clean_prices(rows)["AAA"]
    assert all(c["close"] == 100.0 for c in cleaned), "a weekend print survived"
    assert len(cleaned) == 30


def test_a_split_the_prices_confirm_is_applied_to_the_series():
    from hedge_fund_lab.backtests import _clean_prices

    sessions = _sessions(40)
    rows = [{"date": d, "symbol": "AAA", "close": 100.0 if i < 20 else 25.0, "volume": 100_000}
            for i, d in enumerate(sessions)]
    actions = [{"symbol": "AAA", "action_date": sessions[20], "action_type": "split", "split": "4:1"}]

    cleaned = _clean_prices(rows, actions)["AAA"]
    assert all(abs(bar["close"] - 25.0) < 1e-9 for bar in cleaned), \
        "the pre-split half should be restated onto the post-split share base"


def test_a_contradicted_ratio_is_not_applied():
    """Half the stated ratios disagree with the price series; guessing would
    silently rescale the entire prior history."""
    from hedge_fund_lab.backtests import _clean_prices

    sessions = _sessions(40)
    rows = [{"date": d, "symbol": "AAA", "close": 100.0, "volume": 100_000} for d in sessions]
    actions = [{"symbol": "AAA", "action_date": sessions[20], "action_type": "split", "split": "4:1"}]

    cleaned = _clean_prices(rows, actions)["AAA"]
    assert all(bar["close"] == 100.0 for bar in cleaned)


def test_warehouse_queries_only_reference_columns_that_exist():
    """A SELECT naming a column the table lacks surfaces to the caller as an
    opaque 'warehouse_unavailable', with the real cause in a truncated detail
    string. Adding a non-existent `ratio` column did exactly that in production."""
    import re

    from hedge_fund_lab import backtests
    from institutional_warehouse.schema import TABS

    source = open(backtests.__file__).read()
    tabs = {tab.id: {c.key for c in tab.columns} for tab in TABS}
    checked = 0
    for table_key, tab_id in (("actions_table", "corporate_actions"),
                              ("table", "daily_market_history")):
        pattern = r"SELECT\s+((?:(?!FROM|SELECT).)*?)\s+FROM \{" + table_key + r"\}"
        for match in re.finditer(pattern, source, re.S):
            columns = {
                part.strip().split()[-1]
                for part in match.group(1).split(",")
                if part.strip() and "(" not in part
            }
            missing = columns - tabs[tab_id] - {"*"}
            assert not missing, f"{tab_id} has no column(s) {sorted(missing)}"
            checked += 1
    assert checked >= 2, "the warehouse SELECTs moved; this guard stopped checking"


def test_monthly_history_is_refused_rather_than_annualised_as_daily():
    """daily_market_history is monthly before 2025: median gap 28-30 days, with
    12 bars in 2023 and 12 in 2024. Annualising that by 252 sessions overstates
    the result by about sqrt(20), which is how the momentum backtest came to
    report a 186% annualised return."""
    from datetime import date

    from hedge_fund_lab.backtests import momentum_backtest

    rows = []
    for month in range(1, 13):
        for year in (2022, 2023, 2024, 2025):
            for symbol, growth in (("WIN", 1.02), ("MID", 1.01), ("LOSE", 0.99)):
                rows.append({"date": date(year, month, 15).isoformat(), "symbol": symbol,
                             "close": 100 * growth ** (year * 12 + month), "volume": 100_000})

    result = momentum_backtest(rows, classifications={"WIN": "A", "MID": "B", "LOSE": "C"},
                               config={"holdings": 1, "min_average_daily_value": 1})
    assert result["ok"] is False
    assert result["error"] == "price_history_is_not_daily"
    assert result["price_frequency"]["median_gap_days"] > 20


def test_genuinely_daily_history_still_passes_the_frequency_check():
    from hedge_fund_lab.backtests import _clean_prices, price_frequency_receipt

    rows = [{"date": d, "symbol": "AAA", "close": 100.0, "volume": 1} for d in _sessions(120)]
    receipt = price_frequency_receipt(_clean_prices(rows))
    assert receipt["is_daily"] is True
    assert receipt["median_gap_days"] == 1
    assert receipt["daily_history_appears_to_start"] is not None
