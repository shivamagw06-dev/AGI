"""The sector desk reads historical_valuation, so the daily sweep must fill it.

Yahoo wrote both the multiples and the price into that table. Stopping it as a
source of valuation ratios left CMP with no writer at all, and the sweep that
replaced it only ever wrote the long-format valuation_ratios table. Coverage of
historical_valuation fell from 2,889 rows on 19 August to 82 on the 23rd while
every sweep reported success.
"""

from __future__ import annotations

import inspect
import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT",
                      tempfile.mkdtemp(prefix="wh_hvsync_"))

from valuation_ratios import ingest, sweep


@pytest.fixture()
def warehouse(monkeypatch, tmp_path):
    from institutional_warehouse import db

    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    monkeypatch.delenv("INSTITUTIONAL_WAREHOUSE_DATABASE_URL", raising=False)
    monkeypatch.delenv("WAREHOUSE_DATABASE_URL", raising=False)
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _ratios(symbol, date="2026-08-24"):
    return [{"symbol": symbol, "isin": f"INE{symbol}", "ratio_name": name,
             "company_value": value, "sector_value": 18.0,
             "reported_date": date, "reported_time": f"{date}T12:00:00Z",
             "snapshot_id": f"s-{symbol}-{date}", "provider": "upstox"}
            for name, value in (("pe", 20.1), ("pb", 3.2), ("roe", 14.0))]


def _price(symbol, date, close):
    from institutional_warehouse import gateway

    gateway.write("daily_market_history",
                  [{"symbol": symbol, "date": date, "close": close}],
                  source="test", actor="t")


def _rows():
    from institutional_warehouse import db

    return db.query(
        f"SELECT symbol, date, cmp, pe, pb FROM {db.physical_table('historical_valuation')}")


def test_the_price_comes_from_the_price_table(warehouse):
    _price("AAA", "2026-08-24", 1234.5)
    ingest.sync_historical_valuation(_ratios("AAA"), actor="t")

    row = _rows()[0]
    assert row["cmp"] == 1234.5
    assert row["pe"] == 20.1


def test_a_company_with_no_price_is_left_blank(warehouse):
    """Better no price than one the market never traded at."""
    ingest.sync_historical_valuation(_ratios("BBB"), actor="t")

    assert _rows()[0]["cmp"] is None


def test_a_stale_close_is_not_carried_onto_todays_row(warehouse):
    """The lookup is per date, not "most recent"."""
    _price("AAA", "2026-08-21", 1100.0)          # older only
    ingest.sync_historical_valuation(_ratios("AAA", "2026-08-24"), actor="t")

    row = next(r for r in _rows() if r["date"] == "2026-08-24")
    assert row["cmp"] is None


def test_a_price_already_on_the_row_wins(warehouse):
    """Whoever wrote the row knew more than a close does."""
    from institutional_warehouse import gateway

    gateway.write("historical_valuation",
                  [{"symbol": "AAA", "date": "2026-08-24", "cmp": 999.0}],
                  source="seed", actor="t")
    _price("AAA", "2026-08-24", 1234.5)
    ingest.sync_historical_valuation(_ratios("AAA"), actor="t")

    assert next(r for r in _rows() if r["symbol"] == "AAA")["cmp"] == 999.0


def test_the_daily_sweep_writes_historical_valuation():
    """The whole point: the push-based ingest always did, the sweep did not."""
    src = inspect.getsource(sweep.run)
    assert "sync_historical_valuation" in src


def test_a_failed_pivot_does_not_lose_the_ratios(warehouse):
    """The ratios are already written by then; losing them would be worse."""
    src = inspect.getsource(sweep.run)
    assert "except Exception" in src
    assert '"historical_valuation": valuation' in inspect.getsource(sweep.run)


def test_the_lookups_are_batched_not_per_company(warehouse):
    """A full sweep is 2,400 companies; per-symbol fetches meant 2,400 trips."""
    for fn in (ingest._closing_prices, ingest._existing_valuations):
        assert "IN (" in inspect.getsource(fn)
