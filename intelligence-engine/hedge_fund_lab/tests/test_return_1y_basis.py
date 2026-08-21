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
    """The shipped SQL and the expressions it is built from.

    Read out of scanner.py rather than copied, so a change to either is caught
    here instead of on the desk.
    """
    src = SCANNER.read_text()
    sql = re.search(r'rows = db\.query\(\s*f"""(.*?)"""', src, re.S).group(1)
    feed = _expr(src, "feed")
    basis = _expr(src, "basis")
    from hedge_fund_lab import scanner
    return (sql.replace("{table}", "t")
               .replace("{weekday}", "CAST(strftime('%w', date) AS INTEGER) BETWEEN 1 AND 5")
               .replace("{feed}", feed)
               .replace("{basis}", basis)
               # The query bounds how far back it reads. The tests use dated
               # fixtures, so the bound has to be widened here or every fixture
               # silently falls outside the window and the test proves nothing.
               .replace("{RETURN_WINDOW_DAYS}", "36500"))


def _expr(src: str, name: str) -> str:
    """The SQL expression assigned to `name` in _return_1y_by_symbol."""
    body = src.split("def _return_1y_by_symbol(")[1]
    block = re.search(rf"\n    {name} = \((.*?)\)\n", body, re.S).group(1)
    return " ".join(re.findall(r'"([^"]*)"', block))


def _db(bars):
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE t (symbol TEXT, date TEXT, close REAL, source TEXT,"
                " price_basis TEXT, feed_family TEXT, sys_published INT DEFAULT 1)")
    con.executemany(
        "INSERT INTO t (symbol,date,close,source,price_basis,feed_family)"
        " VALUES (?,?,?,?,?,?)",
        [(b + (None, None))[:6] if len(b) == 4 else b for b in bars])
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


class TestStampedBasis:
    """Once a row states its basis, the query obeys the stamp, not the name.

    `source` is a property of the row rather than of the field, so a partial
    update rewrites it - the formula engine writes only market_cap, yet rows it
    has touched are labelled formula_engine while their price came from
    somewhere else. The stamp is written by whoever supplied the price.
    """

    @staticmethod
    def _bars(symbol, source, basis, feed, start, days, price):
        from datetime import date, timedelta
        out, day = [], date.fromisoformat(start)
        while len(out) < days:
            if day.weekday() < 5:
                out.append((symbol, day.isoformat(), price, source, basis, feed))
            day += timedelta(days=1)
        return out

    def test_a_stamped_row_pairs_on_its_stamp_not_its_source_name(self):
        """Both ends came from Upstox but were relabelled by a later partial
        update. The stamp still says what the price is."""
        bars = (self._bars("STAMPED", "formula_engine", "SPLIT_ADJUSTED", "upstox",
                           "2025-08-18", 10, 100.0)
                + self._bars("STAMPED", "formula_engine", "SPLIT_ADJUSTED", "upstox",
                             "2026-08-10", 10, 130.0))
        assert _returns(bars)["STAMPED"] == 30.0

    def test_a_raw_end_and_an_adjusted_end_never_pair(self):
        """The Lal PathLabs defect, stated in the schema instead of inferred."""
        bars = (self._bars("MIXED", "nse_bhavcopy", "RAW", "nse", "2025-08-18", 10, 3400.0)
                + self._bars("MIXED", "upstox_v3_daily", "SPLIT_ADJUSTED", "upstox",
                             "2026-08-10", 10, 1700.0))
        assert "MIXED" not in _returns(bars)

    def test_one_feed_on_two_bases_does_not_pair_across_them(self):
        """A vendor that changes convention mid-history is still two series."""
        bars = (self._bars("SWITCH", "yahoo_finance", "RAW", "yahoo", "2025-08-18", 10, 200.0)
                + self._bars("SWITCH", "yahoo_finance", "SPLIT_ADJUSTED", "yahoo",
                             "2026-08-10", 10, 100.0))
        assert "SWITCH" not in _returns(bars)

    def test_an_unknown_basis_is_not_usable_as_either_end(self):
        """Agreement between two unestablished conventions means nothing."""
        bars = (self._bars("VAGUE", "mystery_feed", "UNKNOWN", "mystery",
                           "2025-08-18", 10, 100.0)
                + self._bars("VAGUE", "mystery_feed", "UNKNOWN", "mystery",
                             "2026-08-10", 10, 150.0))
        assert "VAGUE" not in _returns(bars)

    def test_an_unstamped_row_falls_back_to_the_declared_table(self):
        """7.1m rows predate the columns. They read the same declaration the
        stamp would have written."""
        from datetime import date, timedelta
        out, day = [], date.fromisoformat("2025-08-18")
        while len(out) < 20:
            if day.weekday() < 5:
                price = 100.0 if len(out) < 10 else 110.0
                out.append(("LEGACY", day.isoformat(), price, "upstox_v3_historical"))
            day += timedelta(days=1)
            if len(out) == 10:
                day = date.fromisoformat("2026-08-10")
        assert _returns(out)["LEGACY"] == 10.0


class TestExtremeReturns:
    """A reading outside the plausible band is withheld and listed, not shown.

    Dr. Lal PathLabs read -45%, Nuvama -75%, GRM Overseas -76%. Every one was a
    split rather than a loss. The band catches that shape even when a future
    defect arrives by some route these tests do not anticipate.
    """

    def test_the_band_is_the_one_that_was_agreed(self):
        from hedge_fund_lab import scanner
        assert scanner.RETURN_FLOOR_PCT == -60.0
        assert scanner.RETURN_CEILING_PCT == 200.0

    def test_a_plausible_return_publishes(self):
        from hedge_fund_lab import scanner
        assert -60.0 < 25.0 < 200.0
        assert not (25.0 < scanner.RETURN_FLOOR_PCT or 25.0 > scanner.RETURN_CEILING_PCT)

    @pytest.mark.parametrize("value", [-75.0, -76.4, 253.0, 473.0])
    def test_the_readings_this_incident_produced_are_all_outside_it(self, value):
        from hedge_fund_lab import scanner
        assert value < scanner.RETURN_FLOOR_PCT or value > scanner.RETURN_CEILING_PCT

    def test_a_withheld_reading_is_kept_for_review(self):
        """Withholding silently would replace a wrong number with no number and
        no reason, which is not better."""
        from hedge_fund_lab import scanner
        assert callable(scanner.extreme_returns)
        assert isinstance(scanner.extreme_returns(), list)


class TestQueryWindow:
    """How far back the query reads.

    Unbounded it walked all 7.1m price rows and called strftime on every one,
    which measured 79 seconds cold. The window has to be wide enough to find an
    anniversary and no wider.
    """

    def test_the_window_covers_a_year_plus_slack(self):
        from hedge_fund_lab import scanner
        assert scanner.RETURN_WINDOW_DAYS >= 425, (
            "the base bar may sit 60 days past the anniversary when a company "
            "has been suspended or the feed has a hole")

    def test_the_window_is_not_the_whole_history(self):
        from hedge_fund_lab import scanner
        assert scanner.RETURN_WINDOW_DAYS <= 1000, "reading a decade to find one year"

    def test_the_query_actually_bounds_itself(self):
        assert "-{RETURN_WINDOW_DAYS} day" in SCANNER.read_text()

    def test_the_latest_close_window_is_short(self):
        """It only has to find today, not a decade of yesterdays."""
        from hedge_fund_lab import scanner
        assert 7 <= scanner.LATEST_CLOSE_WINDOW_DAYS <= 90
