from hedge_fund_lab.backtests import corporate_action_adjustment_receipt


def test_structural_action_adjustment_can_be_independently_verified():
    rows = [
        {"symbol": "AAA", "date": "2026-01-09", "close": 100.0, "adjusted_close": 50.0},
        {"symbol": "AAA", "date": "2026-01-12", "close": 50.0, "adjusted_close": 50.0},
    ]
    actions = [{"symbol": "AAA", "action_date": "2026-01-12", "action_type": "split"}]
    receipt = corporate_action_adjustment_receipt(rows, actions)
    assert receipt["status"] == "PASSED"
    assert receipt["independently_verified"] is True
    assert receipt["structural_actions_verified"] == 1


def test_equal_raw_and_adjusted_prices_do_not_fake_verification():
    rows = [
        {"symbol": "AAA", "date": "2026-01-09", "close": 100.0, "adjusted_close": 100.0},
        {"symbol": "AAA", "date": "2026-01-12", "close": 50.0, "adjusted_close": 50.0},
    ]
    actions = [{"symbol": "AAA", "action_date": "2026-01-12", "action_type": "split"}]
    receipt = corporate_action_adjustment_receipt(rows, actions)
    assert receipt["status"] == "PARTIAL"
    assert receipt["independently_verified"] is False
    assert receipt["structural_actions_verified"] == 0


def test_missing_actions_never_passes_even_with_adjusted_close_coverage():
    rows = [{"symbol": "AAA", "date": "2026-01-09", "close": 100.0, "adjusted_close": 100.0}]
    receipt = corporate_action_adjustment_receipt(rows, [])
    assert receipt["independently_verified"] is False
    assert receipt["corporate_action_rows"] == 0
