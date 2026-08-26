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
