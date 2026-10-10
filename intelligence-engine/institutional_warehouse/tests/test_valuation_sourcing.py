"""Valuation ratios are not sourced from Yahoo."""

from __future__ import annotations

import inspect

from institutional_warehouse import refresh


def test_the_yahoo_stage_does_not_write_historical_valuation():
    """It wrote 918 rows a day because the call predated the sourcing decision.

    Ratios come from Upstox key-ratios and from warehouse_reconstruction over
    the Capital IQ workbook. Yahoo was never chosen for them.
    """
    src = inspect.getsource(refresh.stage_yahoo)
    assert 'gateway.write("historical_valuation"' not in src


def test_the_yahoo_stage_still_writes_prices_and_the_company_master():
    """Prices are a separate sourcing question and are left alone."""
    src = inspect.getsource(refresh.stage_yahoo)
    assert 'gateway.write("daily_market_history"' in src
    assert 'gateway.write("company_master"' in src


def test_the_skip_is_reported_rather_than_silent():
    src = inspect.getsource(refresh.stage_yahoo)
    assert "valuation_not_sourced_from_yahoo" in src
    assert "candidates" in src, "how many rows were dropped must stay visible"
