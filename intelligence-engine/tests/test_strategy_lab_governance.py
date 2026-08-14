from strategy_lab import production


def _row(symbol: str, day: str, close: float = 100.0) -> dict:
    return {
        "symbol": symbol,
        "date": day,
        "close": close,
        "adjusted_close": close,
        "high": close + 1,
        "low": close - 1,
        "volume": 100_000,
    }


def test_common_session_excludes_partial_intraday_and_stale_symbols():
    rows = []
    for ticker in ("A", "B", "C", "D", "E"):
        rows.extend([_row(ticker, "2026-08-12"), _row(ticker, "2026-08-13")])
    rows.append(_row("A", "2026-08-14", 101.0))
    rows = [row for row in rows if not (row["symbol"] == "E" and row["date"] == "2026-08-13")]

    series, health = production._series_snapshot(rows, expected_session="2026-08-13")

    assert health["latest_completed_session"] == "2026-08-13"
    assert health["mixed_session_blocked"] == 1
    assert "E" not in series
    assert series["A"][-1]["date"] == "2026-08-13"


def test_catalog_uses_formal_lifecycle_and_blocks_unimplemented_families():
    assert production.REGISTRY["time_series_momentum"]["lifecycle"] == "IMPLEMENTED"
    assert production.REGISTRY["event_strategies"]["category"] == "BLOCKED"
    assert "EXECUTION_ELIGIBLE" in production.LIFECYCLE

    result = production.scan("event_strategies")

    assert result["ok"] is True
    assert result["status"] == "BLOCKED"
    assert result["signals"] == []
    assert "EVENT_TIMESTAMP_MISSING" in result["reason_codes"]


def test_signal_governance_cannot_self_promote():
    signal = production._govern_signal({
        "signal": "BUY",
        "score": 72,
        "data": {"liquid": True},
        "governance": {},
        "reason_codes": ["POSITIVE_ABSOLUTE_TREND"],
    })

    assert signal["research_direction"] == "LONG"
    assert signal["eligibility"] == "BLOCKED"
    assert signal["trade_eligible"] is False
    assert signal["governance"]["execution"] == "BLOCKED"
    assert "BACKTEST_INSUFFICIENT" in signal["reason_codes"]
    assert "CORPORATE_ACTION_UNVERIFIED" in signal["reason_codes"]
