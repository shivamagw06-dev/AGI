"""Mapping derived observations onto canonical rows."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import canonical_store as cs


RECORD = {
    "trade_date": "2026-08-21", "underlying": "NIFTY", "expiry": "2026-08-25",
    "strike": 24300.0, "option_type": "CE", "dte_days": 4,
    "open": 70.0, "high": 80.0, "low": 65.0, "close": 72.55, "settlement": 72.6,
    "volume": 12345.0, "open_interest": 13469820.0, "change_in_oi": 3683940.0,
    "underlying_close": 24252.0, "forward": 24287.5929,
    "forward_source": "parity", "forward_quality": "high",
    "forward_pair_count": 9, "forward_dispersion_bp": 4.2,
    "moneyness": 1.000512, "log_moneyness": 0.000512,
    "iv": 7.7509, "iv_quality": "ok", "isin": "INE000A01001",
    # present on the live path, deliberately not stored
    "delta": 0.476, "gamma": 0.0007, "theta": -16.68, "vega": 13.79,
}


class RowMapping(unittest.TestCase):
    def test_greeks_are_not_persisted(self):
        # They are functions of columns that are kept. Storing them would cost
        # space on every row of ~8.8M a year to save arithmetic.
        row = cs.to_row(RECORD)
        for greek in ("delta", "gamma", "theta", "vega"):
            self.assertNotIn(greek, row)

    def test_counts_are_integers_not_floats(self):
        # Volume and OI arrive as floats from the CSV parse; bigint columns
        # reject 12345.0 in some drivers and silently truncate in others.
        row = cs.to_row(RECORD)
        for key in ("volume", "open_interest", "change_open_interest"):
            self.assertIsInstance(row[key], int)
        self.assertEqual(row["open_interest"], 13469820)

    def test_a_missing_count_stays_null_rather_than_zero(self):
        # Zero open interest and unknown open interest are different facts.
        row = cs.to_row({**RECORD, "open_interest": None, "volume": None})
        self.assertIsNone(row["open_interest"])
        self.assertIsNone(row["volume"])

    def test_a_refused_volatility_is_null_and_keeps_its_reason(self):
        row = cs.to_row({**RECORD, "iv": None, "iv_quality": "below_intrinsic"})
        self.assertIsNone(row["implied_volatility"])
        self.assertEqual(row["iv_quality"], "below_intrinsic")
        self.assertEqual(row["close_price"], 72.55)   # the observation survives

    def test_every_row_carries_the_versions_that_produced_it(self):
        # Without these a later comparison can mix two methodologies, which is
        # the failure that looks like a discovery.
        row = cs.to_row(RECORD)
        self.assertEqual(row["pipeline_version"], cs.PIPELINE_VERSION)
        self.assertEqual(row["pricing_version"], cs.PRICING_VERSION)
        self.assertEqual(row["source"], "nse_bhavcopy")

    def test_forward_provenance_survives(self):
        row = cs.to_row(RECORD)
        self.assertEqual(row["forward_source"], "parity")
        self.assertEqual(row["forward_quality"], "high")
        self.assertEqual(row["forward_pair_count"], 9)
        self.assertEqual(row["forward_dispersion_bp"], 4.2)


class Upsert(unittest.TestCase):
    def test_a_dry_run_touches_nothing(self):
        with mock.patch.object(cs, "_call") as call, \
             mock.patch.object(cs, "ensure_partition") as part:
            out = cs.upsert([RECORD], dry_run=True)
        call.assert_not_called()
        part.assert_not_called()
        self.assertTrue(out["dry_run"])
        self.assertEqual(out["rows"], 1)

    def test_writing_resolves_duplicates_instead_of_inserting_again(self):
        # Re-ingesting a day must correct it, not double it.
        with mock.patch.object(cs, "_call", return_value=None) as call, \
             mock.patch.object(cs, "ensure_partition", return_value="p"):
            cs.upsert([RECORD], dry_run=False)
        prefer = call.call_args.kwargs["prefer"]
        self.assertIn("merge-duplicates", prefer)

    def test_the_partition_is_ensured_before_the_write(self):
        order = []
        with mock.patch.object(cs, "_call", side_effect=lambda *a, **k: order.append("write")), \
             mock.patch.object(cs, "ensure_partition",
                               side_effect=lambda d: order.append("partition") or "p"):
            cs.upsert([RECORD], dry_run=False)
        self.assertEqual(order[0], "partition")

    def test_a_large_day_goes_up_in_batches(self):
        many = [{**RECORD, "strike": 20000.0 + i} for i in range(cs.BATCH + 250)]
        with mock.patch.object(cs, "_call", return_value=None) as call, \
             mock.patch.object(cs, "ensure_partition", return_value="p"):
            out = cs.upsert(many, dry_run=False)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(out["written"], len(many))

    def test_nothing_to_write_is_not_an_error(self):
        out = cs.upsert([], dry_run=False)
        self.assertTrue(out["ok"])
        self.assertEqual(out["rows"], 0)


class Credentials(unittest.TestCase):
    def test_missing_credentials_say_which_ones(self):
        with mock.patch.dict("os.environ", {"SUPABASE_URL": "", "VITE_SUPABASE_URL": "",
                                            "SUPABASE_SERVICE_ROLE_KEY": ""}, clear=False):
            with self.assertRaises(cs.CanonicalStoreError) as caught:
                cs._credentials()
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", str(caught.exception))


if __name__ == "__main__":
    unittest.main()


class PartitionRefusal(unittest.TestCase):
    def test_a_refused_partition_call_does_not_abandon_the_write(self):
        # Partitions are pre-created by migration, so the helper usually has
        # nothing to do. Failing 828 good rows because it was not allowed to do
        # nothing is the wrong trade.
        calls = []

        def fake(method, path, **kw):
            calls.append(path)
            if "rpc/ensure_option_eod_partition" in path:
                raise cs.CanonicalStoreError(
                    "failed (403): 42501 permission denied for schema public")
            return None

        with mock.patch.object(cs, "_call", side_effect=fake):
            out = cs.upsert([RECORD], dry_run=False)

        self.assertEqual(out["written"], 1)
        self.assertTrue(any(cs.TABLE in c and "rpc" not in c for c in calls),
                        "the rows must still be posted")

    def test_the_refusal_is_reported_rather_than_hidden(self):
        # Swallowing it silently would leave a real missing-partition problem
        # looking like a clean run.
        with mock.patch.object(cs, "_call",
                               side_effect=cs.CanonicalStoreError("403 denied")):
            note = cs.ensure_partition("2026-08-21")
        self.assertIn("unavailable", note)

    def test_a_genuinely_missing_partition_still_fails_the_write(self):
        # The insert is the honest place for that error to surface.
        def fake(method, path, **kw):
            if "rpc/" in path:
                raise cs.CanonicalStoreError("403 denied")
            raise cs.CanonicalStoreError(
                'no partition of relation "option_eod_observation" found')

        with mock.patch.object(cs, "_call", side_effect=fake):
            with self.assertRaises(cs.CanonicalStoreError) as caught:
                cs.upsert([RECORD], dry_run=False)
        self.assertIn("no partition", str(caught.exception))


class SpotHistory(unittest.TestCase):
    """The row cap that made every realised volatility null."""

    def test_it_reads_one_row_per_day_not_one_per_contract(self):
        # Asking the observations for forty days of spot is ~50,000 rows to
        # extract forty numbers, and PostgREST caps the answer silently.
        seen = []

        def fake(method, path, **kw):
            seen.append(path)
            if cs.STATE_TABLE in path:
                return [{"observation_date": f"2026-08-{d:02d}", "spot": 24000.0 + d}
                        for d in range(1, 21)]
            return [{"underlying_spot": 24252.0}]

        with mock.patch.object(cs, "_call", side_effect=fake):
            out = cs.spot_history("2026-08-21", "NIFTY")
        self.assertEqual(len(out), 21)
        state_calls = [p for p in seen if cs.STATE_TABLE in p]
        self.assertEqual(len(state_calls), 1, "one call, not one per day")
        # the observations are asked only for the day being described
        obs_calls = [p for p in seen if cs.TABLE in p and cs.STATE_TABLE not in p]
        self.assertTrue(all("limit=1" in p for p in obs_calls))

    def test_the_day_itself_is_included_even_before_it_has_a_state_row(self):
        def fake(method, path, **kw):
            if cs.STATE_TABLE in path:
                return [{"observation_date": "2026-08-20", "spot": 24232.0}]
            return [{"underlying_spot": 24252.0}]

        with mock.patch.object(cs, "_call", side_effect=fake):
            out = cs.spot_history("2026-08-21", "NIFTY")
        self.assertEqual(out[-1], ("2026-08-21", 24252.0))

    def test_a_missing_state_table_does_not_break_the_first_build(self):
        def fake(method, path, **kw):
            if cs.STATE_TABLE in path:
                raise cs.CanonicalStoreError("404 relation does not exist")
            return [{"underlying_spot": 24252.0}]

        with mock.patch.object(cs, "_call", side_effect=fake):
            out = cs.spot_history("2026-08-21", "NIFTY")
        self.assertEqual(out, [("2026-08-21", 24252.0)])

    def test_it_never_reaches_past_the_day_being_described(self):
        # A realised volatility built from a window reaching forward would be
        # accurate and untradeable.
        seen = {}

        def fake(method, path, **kw):
            seen[path] = True
            return []

        with mock.patch.object(cs, "_call", side_effect=fake):
            cs.spot_history("2026-08-21", "NIFTY")
        state = [p for p in seen if cs.STATE_TABLE in p][0]
        self.assertIn("observation_date=lte.2026-08-21", state)


class Pagination(unittest.TestCase):
    """The silent row cap, which has now cost two results."""

    def _pages(self, total, page=None):
        page = page or cs.PAGE
        seen = []

        def fake(method, path, **kw):
            seen.append(path)
            import re
            off = int(re.search(r"offset=(\d+)", path).group(1))
            lim = int(re.search(r"limit=(\d+)", path).group(1))
            return [{"i": i} for i in range(off, min(off + lim, total))]

        with mock.patch.object(cs, "_call", side_effect=fake):
            rows = cs._call_paged("/rest/v1/thing?x=1")
        return rows, seen

    def test_it_returns_everything_not_the_first_page(self):
        # The studies read 1,000 signals of 3,873 and reported the first 170
        # days as though they were all 651.
        rows, calls = self._pages(3873)
        self.assertEqual(len(rows), 3873)
        self.assertGreater(len(calls), 1)

    def test_it_stops_on_a_short_page(self):
        # The only honest end-of-data signal PostgREST gives.
        rows, calls = self._pages(1500)
        self.assertEqual(len(rows), 1500)
        self.assertEqual(len(calls), 2)

    def test_an_exact_multiple_does_not_lose_the_last_page(self):
        rows, _ = self._pages(cs.PAGE * 2)
        self.assertEqual(len(rows), cs.PAGE * 2)

    def test_an_empty_result_is_not_an_infinite_loop(self):
        rows, calls = self._pages(0)
        self.assertEqual(rows, [])
        self.assertEqual(len(calls), 1)

    def test_it_refuses_to_loop_forever_if_pages_never_shorten(self):
        # A server that always returns a full page would otherwise spin.
        def always_full(method, path, **kw):
            return [{"i": 0}] * cs.PAGE

        with mock.patch.object(cs, "_call", side_effect=always_full):
            rows = cs._call_paged("/rest/v1/thing", max_rows=5000)
        self.assertLessEqual(len(rows), 5000 + cs.PAGE)

    def test_the_query_string_is_preserved_across_pages(self):
        _, calls = self._pages(2500)
        self.assertTrue(all("x=1" in c for c in calls))
