"""The shortability constraint, which decides whether a long-short is real.

An Indian cash-segment short must be squared off the same session, so a
position held across a monthly rebalance needs a single-stock future. There are
214 such underlyings against 1,024 companies carrying a revision signal, so a
decile spread over the full universe is not a portfolio anyone could run.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import shortable as sh


@pytest.fixture(autouse=True)
def _clear():
    sh.reset_cache()
    yield
    sh.reset_cache()


class TestParsing:
    def test_keeps_single_stock_future_underlyings(self):
        rows = [
            {"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "RELIANCE"},
            {"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "TCS"},
        ]
        assert sh.parse_shortable(rows) == {"RELIANCE", "TCS"}

    def test_ignores_options_and_cash(self):
        rows = [
            {"segment": "NSE_FO", "instrument_type": "CE", "underlying_symbol": "RELIANCE"},
            {"segment": "NSE_EQ", "instrument_type": "EQ", "underlying_symbol": "INFY"},
        ]
        assert sh.parse_shortable(rows) == set()

    def test_index_futures_do_not_become_shortable_names(self):
        """An index is not a substitute for the names a stock screen wants."""
        rows = [{"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": ""}]
        assert sh.parse_shortable(rows) == set()

    def test_expiries_of_one_name_collapse_to_one_symbol(self):
        rows = [
            {"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "RELIANCE",
             "expiry": "2026-08-27"},
            {"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "RELIANCE",
             "expiry": "2026-09-24"},
        ]
        assert sh.parse_shortable(rows) == {"RELIANCE"}


class TestCaching:
    def test_the_master_is_downloaded_once(self):
        calls = {"n": 0}

        def _get():
            calls["n"] += 1
            return [{"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "A"}]

        for _ in range(5):
            sh.shortable_symbols(getter=_get)
        assert calls["n"] == 1

    def test_an_outage_returns_empty_rather_than_permitting_everything(self):
        """Unknown must mean "cannot short". A permissive default would
        silently restore the unconstrained result this module prevents."""
        def _boom():
            raise RuntimeError("network down")

        assert sh.shortable_symbols(getter=_boom) == set()

    def test_a_failed_fetch_is_not_cached(self):
        calls = {"n": 0}

        def _flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")
            return [{"segment": "NSE_FO", "instrument_type": "FUT", "underlying_symbol": "A"}]

        assert sh.shortable_symbols(getter=_flaky) == set()
        assert sh.shortable_symbols(getter=_flaky) == {"A"}


class TestBorrowCost:
    def test_one_month_of_an_annual_rate(self):
        # 120bps a year is 1.2%, so one month is 0.1%.
        assert sh.monthly_borrow_cost(120.0) == pytest.approx(0.001)

    def test_negative_rates_are_floored_at_zero(self):
        assert sh.monthly_borrow_cost(-50.0) == 0.0
