"""The registry must cover everything the warehouse holds, and coverage must be a
percentage of something real."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_registry_"))

from institutional_warehouse import db, refresh, store  # noqa: E402
from institutional_warehouse.backfill import coverage  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def test_traded_symbols_are_registered_in_company_master():
    store.upsert(
        "company_master",
        [{"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha Industries",
          "sector": "Industrials"}],
        source="yahoo_finance", actor="tester",
    )
    registered = refresh._register_traded_symbols({"AAA", "BBB", "CCC"}, actor="tester")
    assert registered == 2
    assert set(store.entities("company_master")) == {"AAA", "BBB", "CCC"}


def test_registering_never_overwrites_a_known_company_name():
    """A ticker is not a company name: an existing row must survive the exchange feed."""
    store.upsert(
        "company_master",
        [{"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha Industries",
          "sector": "Industrials"}],
        source="yahoo_finance", actor="tester",
    )
    refresh._register_traded_symbols({"AAA"}, actor="tester")
    row = store.fetch("company_master", entity="AAA")["rows"][0]
    assert row["company_name"] == "Alpha Industries"
    assert row["sector"] == "Industrials"
    assert row["source"] == "yahoo_finance"


def test_a_newly_registered_symbol_carries_only_what_the_feed_knows():
    refresh._register_traded_symbols({"ZZZ"}, actor="tester")
    row = store.fetch("company_master", entity="ZZZ")["rows"][0]
    assert row["symbol"] == "ZZZ"
    assert row["company_name"] == "ZZZ"     # the ticker, not an invented name
    assert row["exchange"] == "NSE"
    assert row["sector"] is None            # nothing is fabricated
    assert row["source"] == "nse_bhavcopy"


def test_coverage_can_never_exceed_one_hundred_percent():
    """The exchange feed runs ahead of the registry; coverage must still make sense."""
    store.upsert(
        "company_master",
        [{"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha"}],
        source="test", actor="tester",
    )
    prices = []
    for symbol in ("AAA", "BBB", "CCC", "DDD"):
        for day in (1, 2, 3):
            prices.append({"symbol": symbol, "date": f"2026-07-0{day}", "close": 100 + day})
    store.upsert("daily_market_history", prices, source="nse_bhavcopy", actor="tester")

    summary = coverage.summary()
    assert summary["registered_companies"] == 1
    assert summary["companies_with_history"] == 4
    assert summary["universe"] == 4
    assert summary["coverage_pct"] <= 100.0


def test_coverage_is_a_true_fraction_once_the_registry_catches_up():
    store.upsert(
        "company_master",
        [{"company_id": s, "symbol": s, "company_name": s} for s in ("AAA", "BBB", "CCC", "DDD")],
        source="test", actor="tester",
    )
    prices = [{"symbol": "AAA", "date": f"2026-07-0{d}", "close": 100 + d} for d in (1, 2, 3)]
    prices += [{"symbol": "BBB", "date": f"2026-07-0{d}", "close": 50 + d} for d in (1, 2, 3)]
    store.upsert("daily_market_history", prices, source="nse_bhavcopy", actor="tester")

    summary = coverage.summary()
    assert summary["universe"] == 4
    assert summary["companies_with_history"] == 2
    assert summary["coverage_pct"] == 50.0
