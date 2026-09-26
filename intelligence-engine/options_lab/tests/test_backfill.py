"""Walking trading days into the warehouse, without fetching any."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import nse_history as nh
from options_lab import canonical_store as cs


REC = {"trade_date": "2026-08-21", "underlying": "NIFTY", "expiry": "2026-08-25",
       "strike": 24300.0, "option_type": "CE", "dte_days": 4, "close": 72.55,
       "forward": 24287.0, "forward_source": "parity", "forward_quality": "high",
       "iv": 7.75, "iv_quality": "ok"}


def patched(*, fetch=None, records=None, upsert=None, stored=None):
    """The backfill with every boundary faked; no HTTP, no sleeping."""
    return (
        mock.patch.object(nh, "fetch_bhavcopy",
                          side_effect=fetch or (lambda d, **k: [{"row": 1}])),
        mock.patch.object(nh, "option_records",
                          side_effect=records or (lambda rows, **k: [REC])),
        mock.patch.object(cs, "upsert",
                          side_effect=upsert or (lambda r, dry_run=True: {
                              "ok": True, "written": len(list(r))})),
        mock.patch.object(cs, "stored_for_day",
                          side_effect=stored or (lambda d, u=None: 0)),
        mock.patch("time.sleep"),
    )


def run(*args, **kwargs):
    patches = patched(**kwargs.pop("fakes", {}))
    for p in patches:
        p.start()
    try:
        return nh.backfill(*args, **kwargs)
    finally:
        for p in patches:
            p.stop()


class TradingDays(unittest.TestCase):
    def test_weekends_are_never_fetched(self):
        # 2026-08-22 and 23 are a Saturday and Sunday.
        days = nh.trading_days("2026-08-21", "2026-08-24")
        self.assertEqual([d.isoformat() for d in days],
                         ["2026-08-21", "2026-08-24"])

    def test_a_single_day_range_is_that_day(self):
        self.assertEqual(nh.trading_days("2026-08-21", "2026-08-21"),
                         [date(2026, 8, 21)])

    def test_a_backwards_range_is_empty_rather_than_infinite(self):
        self.assertEqual(nh.trading_days("2026-08-24", "2026-08-21"), [])


class Chunking(unittest.TestCase):
    def test_a_chunk_stops_at_the_limit_and_says_where(self):
        # A six-month walk outlives the engine's request timeout, so a call
        # does a bounded piece and reports the resume point.
        out = run("2026-08-03", "2026-08-28", dry_run=False, max_days=3)
        self.assertEqual(len(out["ingested"]), 3)
        self.assertEqual(out["resume_from"], "2026-08-06")
        self.assertGreater(out["remaining_days"], 0)

    def test_a_completed_range_has_no_resume_point(self):
        out = run("2026-08-21", "2026-08-21", dry_run=False, max_days=10)
        self.assertIsNone(out["resume_from"])
        self.assertEqual(out["remaining_days"], 0)


class Resuming(unittest.TestCase):
    def test_days_already_stored_are_skipped(self):
        # Resumability with no bookkeeping: the table is the state.
        out = run("2026-08-03", "2026-08-07", dry_run=False, max_days=10,
                  fakes={"stored": lambda d, u=None: 828 if d.day == 4 else 0})
        self.assertIn("2026-08-04", out["skipped_already_present"])
        self.assertNotIn("2026-08-04", [d["day"] for d in out["ingested"]])

    def test_a_dry_run_does_not_consult_the_table(self):
        # Nothing is being written, so "already present" is not a reason to skip.
        calls = []
        out = run("2026-08-21", "2026-08-21", dry_run=True, max_days=5,
                  fakes={"stored": lambda d, u=None: calls.append(d) or 999})
        self.assertEqual(calls, [])
        self.assertEqual(len(out["ingested"]), 1)


class BadDays(unittest.TestCase):
    def test_a_holiday_is_recorded_not_failed(self):
        # NSE has no file for a holiday. Guessing a calendar would be one more
        # thing to keep correct.
        def fetch(day, **k):
            if day.day == 4:
                raise nh.NseHistoryError(f"no bhavcopy for {day.isoformat()}")
            return [{"row": 1}]

        out = run("2026-08-03", "2026-08-05", dry_run=False, max_days=10,
                  fakes={"fetch": fetch})
        self.assertEqual(out["holidays"], ["2026-08-04"])
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["ingested"]), 2)

    def test_one_broken_day_does_not_strand_the_rest(self):
        def fetch(day, **k):
            if day.day == 4:
                raise nh.NseHistoryError("HTTP 500 for 2026-08-04")
            return [{"row": 1}]

        out = run("2026-08-03", "2026-08-05", dry_run=False, max_days=10,
                  fakes={"fetch": fetch})
        self.assertEqual(len(out["ingested"]), 2)
        self.assertEqual(out["failed"][0]["day"], "2026-08-04")
        self.assertFalse(out["ok"])

    def test_a_write_failure_is_attributed_to_its_day(self):
        def upsert(records, dry_run=True):
            raise cs.CanonicalStoreError("no partition found")

        out = run("2026-08-21", "2026-08-21", dry_run=False,
                  fakes={"upsert": upsert})
        self.assertEqual(out["failed"][0]["stage"], "write")
        self.assertIn("no partition", out["failed"][0]["error"])


class Totals(unittest.TestCase):
    def test_written_total_adds_up_across_days(self):
        out = run("2026-08-03", "2026-08-05", dry_run=False, max_days=10)
        self.assertEqual(out["written_total"],
                         sum(d["written"] for d in out["ingested"]))


if __name__ == "__main__":
    unittest.main()


class ArchiveFloor(unittest.TestCase):
    """A 404 from before the archive begins is not a holiday."""

    def test_a_range_before_the_floor_is_refused_whole(self):
        # Swallowed day by day this returns a thousand false holidays, which is
        # a convincing-looking result. The point of the floor is that nobody
        # ever sees one.
        out = nh.backfill("2020-01-01", "2020-03-01", dry_run=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["stage"], "range")
        self.assertIn("2024-01-01", out["error"])

    def test_a_partly_early_range_is_refused_rather_than_trimmed(self):
        # Silently starting later would give a shorter history than asked for,
        # and nothing would say so.
        out = nh.backfill("2023-12-01", "2024-02-01", dry_run=True)
        self.assertFalse(out["ok"])
        self.assertIn("fall before", out["error"])

    def test_a_single_early_day_says_why(self):
        with self.assertRaises(nh.NseHistoryError) as caught:
            nh.fetch_bhavcopy("2023-06-01")
        self.assertIn("earliest", str(caught.exception))

    def test_a_supported_range_still_runs(self):
        out = run("2026-08-19", "2026-08-21", dry_run=True, max_days=3)
        self.assertTrue(out["ok"])
