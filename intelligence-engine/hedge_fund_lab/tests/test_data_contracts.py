from hedge_fund_lab.data_contracts import NEEDS_LATEST_PE, NEEDS_LIVE_PRICE, STRATEGIES, contract_for


def test_intraday_strategies_are_wired_to_live_tape():
    for strategy_id in (
        "opening_range_breakout",
        "intraday_reversion",
        "flow_anomaly",
        "cross_sectional_momentum_v1",
        "live_alpha",
    ):
        assert strategy_id in NEEDS_LIVE_PRICE
        assert "Live" in contract_for(strategy_id)["display_price"] or "live" in contract_for(strategy_id)["display_price"].lower()


def test_value_ranks_on_eod_pe_not_ltp():
    spec = STRATEGIES["value"]
    assert "valuation_ratios" in spec["rank"]
    assert spec["display_price"] != spec["rank"]


def test_groww_rotation_stays_on_daily_candles():
    spec = STRATEGIES["agi_sector_rotation_v1"]
    assert spec["rank"] == spec["display_price"]
    assert "daily" in spec["rank"].lower()
    assert "agi_sector_rotation_v1" not in NEEDS_LATEST_PE
