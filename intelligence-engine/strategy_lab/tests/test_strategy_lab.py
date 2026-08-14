from strategy_lab.production import _breakout, _momentum, _reversion, _trend, dashboard, strategy


def bars(n=300, growth=1.002):
    rows = []
    price = 100.0
    for i in range(n):
        price *= growth
        rows.append({"date": f"2025-{1 + (i // 28) % 12:02d}-{1 + i % 28:02d}", "close": price, "high": price * 1.01, "low": price * .99, "volume": 100_000})
    return rows


def test_phase_one_registry_is_research_only():
    item = strategy("trend_following")
    assert item["ok"] and item["trade_eligible"] is False
    assert item["lifecycle"] == "BACKTESTING"


def test_trend_and_momentum_explain_real_fields():
    trend = _trend("TEST", bars())
    momentum = _momentum("TEST", bars())
    assert trend["signal"] == "BUY"
    assert trend["stop"] < trend["entry"]
    assert "sma200" in trend["factor_contributions"]
    assert momentum["signal"] == "BUY"
    assert momentum["eligibility"] == "RESEARCH_ONLY"


def test_breakout_and_reversion_fail_closed_or_explain():
    breakout = _breakout("TEST", bars(80))
    assert breakout and breakout["trade_eligible"] is False
    down = bars(240)
    for i in range(20):
        down[-20 + i]["close"] *= 1 - (i + 1) * .01
        down[-20 + i]["high"] = down[-20 + i]["close"] * 1.01
        down[-20 + i]["low"] = down[-20 + i]["close"] * .99
    reversion = _reversion("TEST", down)
    assert reversion and "z_score_20" in reversion["factor_contributions"]
