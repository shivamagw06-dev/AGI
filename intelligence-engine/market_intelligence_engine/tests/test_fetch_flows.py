"""FII/DII collection, which had a fetcher that could not authenticate.

The Express service owns the only fetcher and its Upstox token answers
"Invalid token used to access API". Its scheduler was in-memory, targeting
18:05-18:59 IST on a service that redeploys several times a day, and reported
lastRun: null. institutional_flow stopped on 20 August and the refresh route
the engine tells people to call returned 404.
"""

from __future__ import annotations

from market_intelligence_engine import fetch_flows


# Epoch milliseconds, computed rather than guessed.
UTC_20AUG_2100 = 1787259600000   # 2026-08-20 21:00 UTC -> 2026-08-21 02:30 IST
UTC_21AUG_1200 = 1787313600000   # 2026-08-21 12:00 UTC -> 2026-08-21 17:30 IST
UTC_21AUG_1900 = 1787338800000   # 2026-08-21 19:00 UTC -> 2026-08-22 00:30 IST


def test_the_trading_day_is_read_in_ist_not_utc():
    """The offset decides which trading day a stamp belongs to.

    Late-evening UTC is already the next day in IST, and reading it as UTC
    would file an end-of-day print against the wrong session.
    """
    assert fetch_flows._ist_date(UTC_21AUG_1200) == "2026-08-21"
    assert fetch_flows._ist_date(UTC_20AUG_2100) == "2026-08-21"
    assert fetch_flows._ist_date(UTC_21AUG_1900) == "2026-08-22"


def test_a_bad_timestamp_drops_the_row_rather_than_dating_it_today():
    assert fetch_flows._ist_date(None) is None
    assert fetch_flows._ist_date("not-a-number") is None


def test_observations_carry_the_shape_the_normaliser_expects():
    payload = {"data": [{
        "time_stamp": UTC_20AUG_2100, "data_type": "NSE_EQ|CASH",
        "buy_amount": 1200.5, "sell_amount": 900.25,
        "buy_contracts": 10, "total_long_contracts": 7,
    }]}
    rows = fetch_flows._observations(payload, "FII", "1D")

    assert len(rows) == 1
    row = rows[0]
    assert row["participant"] == "FII"
    assert row["segment"] == "NSE_EQ|CASH"
    assert row["buy_amount"] == 1200.5 and row["sell_amount"] == 900.25
    # Renamed to what the warehouse columns are called.
    assert row["long_contracts"] == 7
    assert "total_long_contracts" not in row


def test_dii_rows_carry_no_contract_fields():
    """Contracts are an FII-only concept; DII cash activity has none."""
    payload = {"data": [{"time_stamp": UTC_20AUG_2100, "buy_amount": 5.0, "sell_amount": 4.0}]}
    row = fetch_flows._observations(payload, "DII", "1D")[0]

    assert row["participant"] == "DII"
    assert "long_contracts" not in row


def test_the_normaliser_accepts_what_the_fetcher_produces():
    """The two halves must agree, or the fetch writes nothing."""
    from market_intelligence_engine.ingest_flows import normalise_upstox_flow

    payload = {"data": [{"time_stamp": UTC_20AUG_2100, "data_type": "NSE_EQ|CASH",
                         "buy_amount": 1200.5, "sell_amount": 900.25}]}
    observations = (fetch_flows._observations(payload, "FII", "1D")
                    + fetch_flows._observations(payload, "DII", "1D"))
    rows = normalise_upstox_flow({"observations": observations})

    assert len(rows) == 1
    assert rows[0]["fii_net"] == 300.25
    assert rows[0]["dii_net"] == 300.25


def test_a_token_failure_is_named_not_reported_as_a_quiet_market():
    """"No rows" and "the credential is dead" need different responses, and
    the old failure looked identical to both."""
    import inspect

    src = inspect.getsource(fetch_flows.refresh)
    assert "upstox_returned_no_observations" in src
    assert "failures" in src


def test_it_fetches_a_window_so_a_missed_day_is_recovered():
    """The feed publishes after close; one missed run must not lose a day."""
    import inspect

    src = inspect.getsource(fetch_flows.fetch)
    assert "timedelta(days=10)" in src


def test_no_token_is_reported_rather_than_raised():
    import os

    saved = os.environ.pop("UPSTOX_ACCESS_TOKEN", None)
    try:
        out = fetch_flows._get("/market/fii", [("interval", "1D")])
        assert out == {"ok": False, "error": "no_upstox_token"}
    finally:
        if saved is not None:
            os.environ["UPSTOX_ACCESS_TOKEN"] = saved
