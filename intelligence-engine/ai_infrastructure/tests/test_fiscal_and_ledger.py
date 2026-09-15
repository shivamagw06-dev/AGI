"""Fiscal calendars and the append-only consensus ledger."""

from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_infrastructure import fiscal
from ai_infrastructure.consensus_ledger import LedgerError, build_row, revision


class FiscalCalendars(unittest.TestCase):
    def test_modine_closes_in_march_not_december(self):
        self.assertEqual(fiscal.period_end("MOD", "FY2027"), date(2027, 3, 31))
        self.assertEqual(fiscal.period_end("TT", "FY2027"), date(2027, 12, 31))

    def test_same_label_is_not_the_same_economic_year(self):
        """Trane FY2027 and Modine FY2027 end nine months apart."""
        self.assertFalse(fiscal.periods_are_comparable("TT", "MOD", "FY2027"))
        self.assertTrue(fiscal.periods_are_comparable("TT", "ETN", "FY2027"))

    def test_label_forms_all_normalise(self):
        for label in ("FY27", "FY2027", "2027", "fy 27"):
            self.assertEqual(fiscal.normalise_label(label), "FY2027")

    def test_unknown_symbol_does_not_default_to_december(self):
        """A silent December default is how a March year end disappears."""
        self.assertIsNone(fiscal.period_end("ZZZZ", "FY2027"))

    def test_schneider_is_recorded_as_a_non_filer(self):
        """Its sparse data is a property of the issuer, not a broken loader."""
        self.assertFalse(fiscal.UNIVERSE["SU"].sec_registrant)
        self.assertFalse(fiscal.UNIVERSE["SU"].reports_quarterly)

    def test_backlog_availability_is_recorded_per_company(self):
        """Half the universe does not tag backlog in XBRL, including Trane."""
        self.assertFalse(fiscal.UNIVERSE["TT"].backlog_in_xbrl)
        self.assertFalse(fiscal.UNIVERSE["VRT"].backlog_in_xbrl)
        self.assertTrue(fiscal.UNIVERSE["ETN"].backlog_in_xbrl)


class RowValidation(unittest.TestCase):
    def ok(self, **over):
        args = dict(symbol="TT", metric="eps", fiscal_period="FY2027",
                    consensus_date="2026-08-28", source="capiq", mean=17.48244)
        args.update(over)
        return build_row(**args)

    def test_a_good_row_carries_an_absolute_period_end(self):
        row = self.ok()
        self.assertEqual(row["fiscal_period_end"], "2027-12-31")
        self.assertEqual(row["fiscal_period"], "FY2027")
        self.assertEqual(row["company_name"], "Trane Technologies plc")

    def test_modine_row_gets_the_march_end(self):
        self.assertEqual(self.ok(symbol="MOD")["fiscal_period_end"], "2027-03-31")

    def test_symbol_outside_the_universe_is_refused(self):
        with self.assertRaises(LedgerError):
            self.ok(symbol="AAPL")

    def test_unknown_metric_is_refused(self):
        with self.assertRaises(LedgerError):
            self.ok(metric="vibes")

    def test_a_row_with_no_values_is_refused(self):
        with self.assertRaises(LedgerError):
            self.ok(mean=None)

    def test_a_future_vintage_date_is_refused(self):
        ahead = (date.today() + timedelta(days=2)).isoformat()
        with self.assertRaises(LedgerError):
            self.ok(consensus_date=ahead)

    def test_an_estimate_for_a_closed_year_is_refused(self):
        """FY2024 estimated in 2026 is a restatement, not a forward consensus."""
        with self.assertRaises(LedgerError):
            self.ok(fiscal_period="FY2024")

    def test_inverted_dispersion_is_refused(self):
        with self.assertRaises(LedgerError):
            self.ok(low=20.0, high=10.0)

    def test_dispersion_and_breadth_survive_the_round_trip(self):
        row = self.ok(median=17.5, high=19.2, low=15.1, analyst_count=21,
                      upward_revisions=20, downward_revisions=1)
        self.assertEqual(row["analyst_count"], 21)
        self.assertEqual(row["upward_revisions"], 20)
        self.assertEqual(row["downward_revisions"], 1)
        self.assertAlmostEqual(row["high_estimate"], 19.2)


class Revisions(unittest.TestCase):
    def series(self, *pairs, symbol="TT", period="FY2027"):
        return [{"symbol": symbol, "fiscal_period": period,
                 "consensus_date": d, "mean_estimate": v} for d, v in pairs]

    def test_one_vintage_is_not_a_flat_revision(self):
        """The exact state the current warehouse is in for FY2027."""
        self.assertIsNone(revision(self.series(("2026-08-28", 17.48)), date(2026, 8, 28)))

    def test_a_real_revision_is_measured(self):
        got = revision(self.series(("2026-05-01", 16.0), ("2026-08-28", 17.6)),
                       date(2026, 8, 28), lookback_days=90)
        self.assertAlmostEqual(got["revision_pct"], 10.0, places=3)
        self.assertEqual(got["from_date"], "2026-05-01")

    def test_a_lookback_predating_all_history_yields_nothing(self):
        self.assertIsNone(revision(self.series(("2026-05-01", 16.0), ("2026-08-28", 17.6)),
                                   date(2026, 8, 28), lookback_days=400))

    def test_mixing_two_fiscal_periods_raises(self):
        """Silently differencing FY2027 against FY2028 reports a year of growth."""
        rows = (self.series(("2026-05-01", 16.0))
                + self.series(("2026-08-28", 19.0), period="FY2028"))
        with self.assertRaises(LedgerError):
            revision(rows, date(2026, 8, 28))

    def test_future_vintages_are_invisible(self):
        got = revision(self.series(("2026-05-01", 16.0), ("2026-08-28", 17.6),
                                   ("2026-12-01", 99.0)), date(2026, 8, 28))
        self.assertAlmostEqual(got["to_value"], 17.6)


if __name__ == "__main__":
    unittest.main()
