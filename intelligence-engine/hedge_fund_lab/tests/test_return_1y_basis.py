"""The one-year return has to take both ends from the same price convention.

Three feeds write daily_market_history. Upstox supplies prices already adjusted
for splits and bonuses; the NSE bhavcopy supplies the raw price that traded.
Both land in `close`, and the table keeps one row per symbol and day, so a
series can start on one convention and finish on the other. The ratio between
the two endpoints then carries the split factor rather than the return.

Dr. Lal PathLabs split two-for-one and was published at -45.29% for a year it
finished up about 12%. These run the real query against a series built to flip
convention exactly the way the stored one did.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

SCANNER = Path(__file__).resolve().parents[1] / "scanner.py"


def _query() -> str:
    """The shipped SQL, so a change to it is caught here rather than in production."""
    src = SCANNER.read_text()
    sql = re.search(r'rows = db\.query\(\s*f"""(.*?)"""', src, re.S).group(1)
    return (sql.replace("{table}", "t")
               .replace("{weekday}", "CAST(strftime('%w', date) AS INTEGER) BETWEEN 1 AND 5")
               .replace("{feed}", "CASE WHEN source LIKE 'upstox%' THEN 'upstox'"
                                  " WHEN source LIKE 'yahoo%' THEN 'yahoo' ELSE source END"))


def _db(bars):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE t (symbol TEXT, date TEXT, close REAL, source TEXT,"
                " sys_published INT DEFAULT 1)")
    con.executemany("INSERT INTO t (symbol,date,close,source) VALUES (?,?,?,?)", bars)
    return con


def _returns(bars):
    out = {}
    for row in _db(bars).execute(_query()):
        out[row["symbol"]] = round((row["last_close"] / row["base_close"] - 1) * 100, 1)
    return out


def _series(symbol, source, start, days, price):
    """Weekday bars at a flat price, so any move in a test is one the test made."""
    from datetime import date, timedelta
    out, day = [], date.fromisoformat(start)
    while len(out) < days:
        if day.weekday() < 5:
            out.append((symbol, day.isoformat(), price, source))
        day += timedelta(days=1)
    return out


class TestOneConvention:
    def test_a_series_that_flips_convention_does_not_report_the_split_as_a_return(self):
        """The raw leg is twice the adjusted leg because the stock split
        two-for-one. Pairing across the join reports -50% for a flat year."""
        raw = _series("SPLITCO", "nse_bhavcopy", "2025-08-18", 12, 3400.0)
        adjusted = _series("SPLITCO", "upstox_v3_historical", "2026-08-03", 12, 1700.0)
        got = _returns(raw + adjusted)
        assert "SPLITCO" not in got, "no single feed spans the year, so nothing is claimed"

    def test_a_feed_that_spans_the_year_is_used(self):
        bars = (_series("GOODCO", "upstox_v3_historical", "2025-08-18", 10, 100.0)
                + _series("GOODCO", "upstox_v3_historical", "2026-08-10", 10, 125.0))
        assert _returns(bars)["GOODCO"] == 25.0

    def test_the_two_upstox_writers_count_as_one_feed(self):
        """The deep backfill writes `upstox_v3_historical` and the nightly
        top-up writes `upstox_v3_daily`. Treated as different feeds, the deep
        one fails the freshness test and the fresh one has no history, so the
        desk falls back to a stale uploaded file."""
        bars = (_series("PAIRCO", "upstox_v3_historical", "2025-08-18", 10, 100.0)
                + _series("PAIRCO", "upstox_v3_daily", "2026-08-10", 10, 120.0))
        assert _returns(bars)["PAIRCO"] == 20.0

    def test_the_raw_feed_is_used_when_it_is_the_only_one(self):
        """A delisted company exists nowhere else, and a raw series is internally
        consistent - the rule is one convention, not one preferred vendor."""
        bars = (_series("ONLYRAW", "nse_bhavcopy", "2025-08-18", 10, 50.0)
                + _series("ONLYRAW", "nse_bhavcopy", "2026-08-10", 10, 40.0))
        assert _returns(bars)["ONLYRAW"] == -20.0

    def test_the_deeper_feed_wins_when_both_span_the_year(self):
        deep = (_series("BOTH", "upstox_v3_historical", "2025-08-18", 60, 100.0)
                + _series("BOTH", "upstox_v3_historical", "2026-08-10", 10, 150.0))
        shallow = (_series("BOTH", "formula_engine", "2025-08-19", 1, 100.0)
                   + _series("BOTH", "formula_engine", "2026-08-11", 1, 200.0))
        assert _returns(deep + shallow)["BOTH"] == 50.0


class TestGuards:
    def test_a_feed_that_stopped_months_ago_cannot_serve_a_stale_return(self):
        """Its last bar is its own latest, so without the check it would happily
        report a year that ended in March."""
        stale = (_series("STALE", "yahoo_finance", "2025-02-03", 10, 100.0)
                 + _series("STALE", "yahoo_finance", "2026-02-02", 10, 300.0))
        fresh = _series("STALE", "upstox_v3_daily", "2026-08-10", 10, 110.0)
        got = _returns(stale + fresh)
        assert got.get("STALE") != 200.0, "the year ending in February must not be published"

    def test_a_base_far_older_than_the_anniversary_is_not_used(self):
        """A feed whose history starts three years back would otherwise report a
        three-year move as a one-year one."""
        bars = (_series("OLD", "upstox_v3_historical", "2022-08-18", 10, 10.0)
                + _series("OLD", "upstox_v3_historical", "2026-08-10", 10, 90.0))
        assert "OLD" not in _returns(bars)

    def test_weekend_bars_are_ignored(self):
        """NSE does not trade at the weekend and those rows carry a differently
        scaled series."""
        bars = (_series("WKND", "upstox_v3_historical", "2025-08-18", 10, 100.0)
                + [("WKND", "2025-08-23", 999.0, "formula_engine")]
                + _series("WKND", "upstox_v3_historical", "2026-08-10", 10, 110.0))
        assert _returns(bars)["WKND"] == 10.0
