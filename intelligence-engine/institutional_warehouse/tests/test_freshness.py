"""Staleness has to be judged against cadence, not a fixed number of days."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT",
                      tempfile.mkdtemp(prefix="wh_fresh_"))

from institutional_warehouse import freshness


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


def _row(tab, **fields):
    from institutional_warehouse import gateway

    gateway.write(tab, [fields], source="test", actor="t")


def _status(out, tab):
    return next(t for t in out["tables"] if t["tab"] == tab)


def test_a_daily_table_two_days_old_is_fine(warehouse):
    """A Monday reading Friday's close is a weekend, not a broken collector."""
    _row("daily_market_history", symbol="AAA", date="2026-08-21", close=10.0)
    out = freshness.report(today="2026-08-23")

    assert _status(out, "daily_market_history")["status"] == freshness.OK


def test_a_daily_table_a_week_old_is_late(warehouse):
    _row("daily_market_history", symbol="AAA", date="2026-08-14", close=10.0)
    out = freshness.report(today="2026-08-23")

    row = _status(out, "daily_market_history")
    assert row["status"] == freshness.LATE
    assert row["age_days"] == 9


def test_the_frozen_archive_is_not_reported_as_stale(warehouse):
    """CapIQ fiscal-year data has not moved since March 2025 and should not.

    A single day threshold would flag it every morning, and an alert that is
    always on is one nobody reads.
    """
    _row("sector_ratio_history", symbol="AAA", fiscal_year="FY25",
         metric="pe", source_version="v1", as_of="2025-03-31", value=20.0)
    out = freshness.report(today="2026-08-23")

    assert _status(out, "sector_ratio_history")["status"] == freshness.OK


def test_an_event_table_gets_a_longer_quiet_period(warehouse):
    """No insider filings for four days is a quiet week, not a failure."""
    _row("insider_trades", company_name="A Ltd", person="P",
         reported_on="2026-08-19", action="Acquisition", quantity=1.0,
         mode="Market Purchase")
    out = freshness.report(today="2026-08-23")

    assert _status(out, "insider_trades")["status"] == freshness.OK


def test_an_empty_table_is_distinguished_from_a_stale_one(warehouse):
    """Never collected and stopped collecting need different responses."""
    out = freshness.report(today="2026-08-23")

    assert _status(out, "institutional_flow")["status"] == freshness.EMPTY
    assert _status(out, "institutional_flow")["rows"] == 0


def test_it_names_the_desk_not_only_the_table(warehouse):
    """"institutional_flow is late" means nothing to whoever reads the alert."""
    out = freshness.report(today="2026-08-23")

    assert out["ok"] is False
    assert any("flows" in reader for reader in out["affected_readers"])


def test_everything_current_reports_ok(warehouse):
    for tab, fields in (
        ("daily_market_history", {"symbol": "AAA", "date": "2026-08-23", "close": 1.0}),
        ("valuation_ratios", {"symbol": "AAA", "isin": "INEA", "ratio_name": "pe",
                              "company_value": 1.0, "reported_date": "2026-08-23",
                              "snapshot_id": "s1"}),
    ):
        _row(tab, **fields)
    out = freshness.report(today="2026-08-23")

    assert _status(out, "daily_market_history")["status"] == freshness.OK
    assert _status(out, "valuation_ratios")["status"] == freshness.OK


def test_a_row_with_no_measurement_does_not_make_a_feed_look_current(warehouse):
    """The failure this monitor exists to catch, caused by the monitor itself.

    An empty POST to the flows ingest wrote a row carrying today's date, the
    default segment and no figures. It sat at the top of institutional_flow
    and the first version of this report called the table healthy, which is
    the exact blindness it was written to remove.
    """
    _row("institutional_flow", date="2026-08-20", segment="NSE_EQ|CASH", interval="1D",
         fii_net=-583.36, dii_net=3537.71)
    _row("institutional_flow", date="2026-08-23", segment="NSE_EQ", interval="1D")  # no figures

    out = freshness.report(today="2026-08-27")
    row = _status(out, "institutional_flow")

    # Judged on the 20th, the last day carrying a number - not the 23rd.
    assert row["newest"] == "2026-08-20"
    assert row["status"] == freshness.LATE


def test_a_row_with_one_side_populated_still_counts(warehouse):
    """A day where only DII reported is a real observation."""
    _row("institutional_flow", date="2026-08-23", segment="NSE_EQ", interval="1D", dii_net=120.5)

    out = freshness.report(today="2026-08-23")
    assert _status(out, "institutional_flow")["newest"] == "2026-08-23"
    assert _status(out, "institutional_flow")["status"] == freshness.OK


def test_a_price_row_with_no_close_does_not_count(warehouse):
    _row("daily_market_history", symbol="AAA", date="2026-08-21", close=10.0)
    _row("daily_market_history", symbol="BBB", date="2026-08-23")   # no close

    out = freshness.report(today="2026-08-23")
    assert _status(out, "daily_market_history")["newest"] == "2026-08-21"
