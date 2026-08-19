"""The receipt that gates alpha claims on corporate-action integrity.

It used to certify the warehouse's `adjusted_close`. That column equals `close`
wherever populated and reflects no structural action at all, so the receipt was
auditing a field nothing consumed and reporting 98.6% "coverage" while 0 of 114
actions were actually verified. It now audits the adjustment this module
applies, corroborated against the price gap.
"""

from datetime import date, timedelta

from hedge_fund_lab.backtests import corporate_action_adjustment_receipt, price_point_in_time_receipt


def _bars(symbol: str, start: date, count: int, close: float) -> list[dict]:
    out, day = [], start
    while len(out) < count:
        if day.weekday() < 5:
            out.append({"symbol": symbol, "date": day.isoformat(), "close": close})
        day += timedelta(days=1)
    return out


def _around(symbol: str, ex: date, pre: float, post: float, count: int = 5) -> list[dict]:
    """Contiguous sessions either side of an ex-date, as a real series looks."""
    before, day = [], ex - timedelta(days=1)
    while len(before) < count:
        if day.weekday() < 5:
            before.append({"symbol": symbol, "date": day.isoformat(), "close": pre})
        day -= timedelta(days=1)
    return sorted(before, key=lambda r: r["date"]) + _bars(symbol, ex, count, post)


def test_a_split_the_prices_confirm_is_corroborated():
    rows = _around("AAA", date(2026, 2, 2), 100.0, 50.0)
    actions = [{"symbol": "AAA", "action_date": "2026-02-02", "action_type": "split", "split": "2:1"}]
    receipt = corporate_action_adjustment_receipt(rows, actions)
    assert receipt["status"] == "PASSED"
    assert receipt["independently_verified"] is True
    assert receipt["structural_actions_corroborated"] == 1


def test_a_stated_ratio_the_prices_contradict_is_quarantined():
    """DELPHIFX states a 3:1 split against a 16.4x price gap. Applying the
    stated factor would silently rescale the whole prior history."""
    rows = _around("BAD", date(2026, 2, 2), 100.0, 99.0)
    actions = [{"symbol": "BAD", "action_date": "2026-02-02", "action_type": "split", "split": "4:1"}]
    receipt = corporate_action_adjustment_receipt(rows, actions)
    assert receipt["independently_verified"] is False
    assert receipt["structural_actions_contradicted"] == 1
    assert receipt["structural_actions_corroborated"] == 0


def test_weekend_rows_are_reported_as_dropped():
    """NSE does not trade on Sunday; those rows carry a differently scaled
    series and would fabricate a -90% session followed by a +900% one."""
    rows = _bars("AAA", date(2026, 1, 5), 4, 100.0) + [
        {"symbol": "AAA", "date": "2026-01-11", "close": 10.0},  # Sunday
    ]
    receipt = corporate_action_adjustment_receipt(rows, [])
    assert receipt["non_trading_day_rows_dropped"] == 1
    assert receipt["price_rows"] == 4


def test_missing_actions_never_passes():
    rows = _bars("AAA", date(2026, 1, 5), 4, 100.0)
    receipt = corporate_action_adjustment_receipt(rows, [])
    assert receipt["independently_verified"] is False
    assert receipt["corporate_action_rows"] == 0


def test_price_only_pit_receipt_requires_prior_signal_and_future_execution():
    passed = price_point_in_time_receipt({
        "ok": True,
        "validation": {"lookahead_check": True},
        "execution": {"signal_time": "prior_close", "execution": "next_close"},
    })
    failed = price_point_in_time_receipt({
        "ok": True,
        "validation": {"lookahead_check": True},
        "execution": {"signal_time": "same_close", "execution": "same_close"},
    })
    assert passed["status"] == "EXACT"
    assert passed["fundamental_filing_dates_required"] is False
    assert failed["status"] == "FAILED"
