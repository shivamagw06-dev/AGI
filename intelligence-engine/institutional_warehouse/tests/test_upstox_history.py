"""Upstox daily history, and the check that would have caught the Yahoo failure.

The Yahoo stage reported 2,710 companies done and 0 failed while writing about
245 rows each, because it never asked whether what came back was daily. It was
monthly. Every assertion about granularity here exists to stop that recurring.
"""

from __future__ import annotations

from datetime import date

import pytest

from institutional_warehouse.backfill.sources import upstox_history as uh


class TestInstrumentKey:
    def test_uses_the_stored_key_when_present(self):
        assert uh.instrument_key({"instrument_key": "NSE_EQ|INE002A01018"}) == "NSE_EQ|INE002A01018"

    def test_derives_the_key_from_an_isin(self):
        """2,431 companies carry an ISIN against 2,014 with a key stored."""
        assert uh.instrument_key({"isin": "INE466L01038"}) == "NSE_EQ|INE466L01038"

    def test_rejects_anything_that_is_not_an_isin(self):
        for bad in ({}, {"isin": ""}, {"isin": "RELIANCE"}, {"isin": "12345"}):
            assert uh.instrument_key(bad) is None


class TestWindows:
    def test_splits_a_long_span_because_upstox_rejects_it(self):
        """A 2015-2026 request returns UDAPI1148 'Invalid date range'."""
        spans = uh.windows(date(2000, 1, 1), date(2026, 8, 19))
        assert len(spans) >= 3
        assert all((hi - lo).days <= 366 * 10 for lo, hi in spans)

    def test_is_newest_first_so_a_partial_run_keeps_recent_history(self):
        spans = uh.windows(date(2000, 1, 1), date(2026, 8, 19))
        assert spans[0][1] > spans[-1][1]

    def test_covers_the_whole_span_without_a_hole(self):
        spans = uh.windows(date(2000, 1, 1), date(2026, 8, 19))
        assert spans[0][1] == date(2026, 8, 19)
        assert spans[-1][0] == date(2000, 1, 1)
        for newer, older in zip(spans, spans[1:]):
            assert newer[0] == older[1], "windows must abut"

    def test_handles_a_leap_day_endpoint(self):
        assert uh.windows(date(2000, 1, 1), date(2024, 2, 29))


class TestParseCandles:
    def test_maps_a_candle_onto_warehouse_columns(self):
        payload = {"data": {"candles": [
            ["2026-08-18T00:00:00+05:30", 100.0, 105.0, 99.0, 104.0, 12345, 0],
        ]}}
        row = uh.parse_candles(payload, symbol="AAA")[0]
        assert row["date"] == "2026-08-18"
        assert (row["open"], row["high"], row["low"], row["close"]) == (100.0, 105.0, 99.0, 104.0)
        assert row["volume"] == 12345
        assert row["source"] == uh.SOURCE

    def test_adjusted_close_carries_the_adjusted_series(self):
        """Upstox candles are already adjusted - RELIANCE runs through its
        September 2017 1:1 bonus at about 389 with no break - unlike the
        warehouse column, which equalled close while reflecting no action."""
        payload = {"data": {"candles": [["2026-08-18T00:00:00+05:30", 1, 2, 0.5, 1.5, 10, 0]]}}
        row = uh.parse_candles(payload, symbol="AAA")[0]
        assert row["adjusted_close"] == row["close"] == 1.5

    def test_drops_malformed_and_non_positive_candles(self):
        payload = {"data": {"candles": [
            ["2026-08-18T00:00:00+05:30", 1, 2, 0.5, 0, 10, 0],       # zero close
            ["2026-08-17T00:00:00+05:30", 1, 2, 0.5, None, 10, 0],    # no close
            ["not-a-date", 1, 2, 0.5, 1.5, 10, 0],                    # unparseable
            ["2026-08-14T00:00:00+05:30", 1, 2],                      # truncated
        ]}}
        assert uh.parse_candles(payload, symbol="AAA") == []

    def test_empty_payloads_are_safe(self):
        for payload in ({}, {"data": {}}, {"data": {"candles": []}}):
            assert uh.parse_candles(payload, symbol="AAA") == []


class TestDailyShare:
    def test_daily_series_scores_one(self):
        rows = [{"date": d} for d in
                ("2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14")]
        assert uh.daily_share(rows) == pytest.approx(1.0)

    def test_weekend_gaps_still_count_as_daily(self):
        rows = [{"date": d} for d in ("2026-08-14", "2026-08-17", "2026-08-18")]
        assert uh.daily_share(rows) == pytest.approx(1.0)

    def test_a_monthly_series_scores_zero(self):
        """This is what the Yahoo stage actually returned, and reported as done."""
        rows = [{"date": f"2024-{m:02d}-15"} for m in range(1, 13)]
        assert uh.daily_share(rows) == 0.0


class TestFetchHistory:
    def test_stitches_windows_and_deduplicates_overlap(self):
        def getter(url):
            return {"data": {"candles": [
                ["2020-01-02T00:00:00+05:30", 1, 2, 0.5, 10.0, 100, 0],
                ["2020-01-03T00:00:00+05:30", 1, 2, 0.5, 11.0, 100, 0],
            ]}}

        out = uh.fetch_history("AAA", "NSE_EQ|INE002A01018",
                               start=date(2000, 1, 1), end=date(2026, 8, 19), getter=getter)
        assert out["ok"] is True
        assert len(out["prices"]) == 2, "the same bar returned by two windows must collapse"
        assert out["first"] == "2020-01-02" and out["last"] == "2020-01-03"

    def test_a_window_before_listing_does_not_fail_the_company(self):
        """Upstox errors rather than returning an empty set before listing."""
        import urllib.error

        calls = {"n": 0}

        def getter(url):
            calls["n"] += 1
            if calls["n"] > 1:
                raise urllib.error.HTTPError(url, 400, "Invalid date range", None, None)
            return {"data": {"candles": [["2026-08-18T00:00:00+05:30", 1, 2, 0.5, 10.0, 5, 0]]}}

        out = uh.fetch_history("AAA", "NSE_EQ|INE002A01018",
                               start=date(2000, 1, 1), end=date(2026, 8, 19), getter=getter)
        assert out["ok"] is True
        assert out["prices"] and out["errors"]

    def test_reports_failure_when_nothing_comes_back(self):
        out = uh.fetch_history("AAA", "NSE_EQ|INE002A01018",
                               start=date(2020, 1, 1), end=date(2021, 1, 1),
                               getter=lambda url: {"data": {"candles": []}})
        assert out["ok"] is False
        assert out["error"] == "no_candles_returned"


class TestDuplicateKeys:
    def test_duplicate_symbol_date_rows_are_collapsed_before_writing(self):
        """daily_market_history keys on (symbol, date) and the store has no
        ON CONFLICT clause: two rows sharing a key both land in the insert
        batch and fail the whole run with a UNIQUE constraint error, which is
        what killed a 25-company batch."""
        from institutional_warehouse.backfill.prices_upstox import _one_row_per_key

        rows = [
            {"symbol": "AAA", "date": "2026-08-18", "close": 1.0},
            {"symbol": "AAA", "date": "2026-08-18", "close": 2.0},
            {"symbol": "AAA", "date": "2026-08-17", "close": 3.0},
        ]
        out = _one_row_per_key(rows)
        assert len(out) == 2
        assert [r for r in out if r["date"] == "2026-08-18"][0]["close"] == 2.0, "last wins"

    def test_case_differences_in_symbol_still_collide(self):
        from institutional_warehouse.backfill.prices_upstox import _one_row_per_key

        rows = [{"symbol": "aaa", "date": "2026-08-18", "close": 1.0},
                {"symbol": "AAA", "date": "2026-08-18", "close": 2.0}]
        assert len(_one_row_per_key(rows)) == 1


def test_one_failing_company_does_not_abort_the_batch(monkeypatch):
    """A raising write previously aborted the whole stage, so 24 healthy
    companies were lost to one bad payload."""
    from institutional_warehouse.backfill import prices_upstox as pu

    monkeypatch.setattr(pu, "_companies", lambda: {"AAA": "NSE_EQ|INE000000001",
                                                   "BBB": "NSE_EQ|INE000000002"})
    monkeypatch.setattr(pu.checkpoints, "pending_entities", lambda *a, **k: ["AAA", "BBB"])
    monkeypatch.setattr(pu.checkpoints, "save_checkpoint", lambda *a, **k: None)
    monkeypatch.setattr(pu.checkpoints, "entity_coverage", lambda *a, **k: {})

    def _company(symbol, **kwargs):
        if symbol == "AAA":
            raise RuntimeError("UNIQUE constraint failed: wh_daily_market_history.row_id")
        return {"ok": True, "symbol": symbol, "rows": 10, "first": "2000-01-03"}

    monkeypatch.setattr(pu, "backfill_company", _company)
    out = pu.backfill()
    assert out["companies_done"] == 1
    assert out["companies_failed"] == 1
    assert "UNIQUE constraint" in out["failures"][0]["error"]
