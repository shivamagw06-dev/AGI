from strategy_lab.production import (
    _breakout,
    _cross_sectional_momentum,
    _momentum,
    _reversion,
    _trend,
    dashboard,
    strategy,
)
from strategy_lab.validation_registry import normalise_evidence


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
    assert item["lifecycle"] == "IMPLEMENTED"
    assert item["validation_registry"]["authority"] == "VALIDATION_REGISTRY"
    assert item["validation_registry"]["execution"] == "BLOCKED"


def test_registry_canonicalises_operational_pass_fail_labels():
    evidence = normalise_evidence({
        "data_freshness": {"status": "PASS"},
        "data_completeness": {"status": "FAIL"},
        "risk": {"status": "ERROR"},
    })
    assert evidence["data_freshness"]["status"] == "PASSED"
    assert evidence["data_completeness"]["status"] == "FAILED"
    assert evidence["risk"]["status"] == "FAILED"


def test_trend_and_momentum_explain_real_fields():
    trend = _trend("TEST", bars())
    momentum = _momentum("TEST", bars())
    assert trend["signal"] == "BUY"
    assert trend["stop"] < trend["entry"]
    assert "sma200" in trend["factor_contributions"]
    assert momentum["signal"] == "BUY"
    assert momentum["eligibility"] == "BLOCKED"


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


def test_cross_sectional_momentum_is_registered_as_implemented():
    result = strategy("cross_sectional_momentum", {
        "session_status": "PASS",
        "latest_completed_session": "2026-08-14",
        "session_coverage": 200,
        "coverage_threshold": 160,
    })
    assert result["calculator_available"] is True
    assert result["validation_registry"]["evidence"]["implementation"]["status"] == "PASSED"
    assert result["execution_eligible"] is False


def test_cross_sectional_scanner_ranks_same_session_universe():
    series = {f"S{index}": bars(253, 1.0005 + index / 100_000) for index in range(25)}
    signals = _cross_sectional_momentum(series)
    assert len(signals) == 25
    assert sum(signal["signal"] == "BUY" for signal in signals) == 20
    assert signals[0]["factor_contributions"]["cross_sectional_rank"] == 1
    assert all(signal["trade_eligible"] is False for signal in signals)


def test_runtime_registry_refresh_preserves_durable_validation_evidence(monkeypatch):
    monkeypatch.setattr("strategy_lab.registry_store.load_latest_evidence", lambda: {
        "cross_sectional_momentum": {
            "parameter_stability": {"status": "FAILED", "source": "backtest", "detail": "unstable"},
            "corporate_actions": {"status": "PARTIAL", "source": "adjustment_receipt"},
        }
    })
    result = strategy("cross_sectional_momentum", {
        "session_status": "PASS",
        "latest_completed_session": "2026-08-14",
        "session_coverage": 200,
        "coverage_threshold": 160,
    })
    evidence = result["validation_registry"]["evidence"]
    assert evidence["parameter_stability"]["status"] == "FAILED"
    assert evidence["corporate_actions"]["status"] == "PARTIAL"
