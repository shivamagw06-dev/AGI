"""Signals, outcomes, and the wall between them."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import outcomes as oc
from options_lab import signals as sg


def state(day, *, iv=12.0, rr=-1.5, pcr=1.0, spot=24000.0, rv=11.0,
          gap=-0.2, agree=1.0, quality="high"):
    return {"observation_date": day, "underlying_symbol": "NIFTY",
            "atm_iv_30d": iv, "risk_reversal_30d": rr, "oi_pcr": pcr,
            "spot": spot, "realised_vol_20d": rv, "iv_minus_trailing_rv": iv - rv,
            "spot_to_max_pain_pct": gap, "skew_agreement": agree,
            "state_quality": quality}


def history(n, **kw):
    return [state(f"2026-06-{i+1:02d}", **kw) for i in range(n)]


class Zscores(unittest.TestCase):
    def test_a_short_history_gives_no_zscore_rather_than_a_shaky_one(self):
        # The same mistake the twenty-day realised volatility made.
        z, n = sg._zscore(12.0, [11.0] * 5)
        self.assertIsNone(z)
        self.assertEqual(n, 5)

    def test_a_constant_history_cannot_call_anything_unusual(self):
        # Dividing by a zero spread would report infinity as a discovery.
        z, _ = sg._zscore(12.0, [11.0] * 40)
        self.assertIsNone(z)

    def test_a_value_above_its_own_past_scores_positive(self):
        hist = [10.0 + (i % 5) * 0.5 for i in range(40)]
        z, _ = sg._zscore(20.0, hist)
        self.assertGreater(z, 3)

    def test_only_the_recent_window_counts(self):
        old = [50.0] * 200
        recent = [10.0 + (i % 3) for i in range(sg.LOOKBACK)]
        z, n = sg._zscore(11.0, old + recent)
        self.assertLessEqual(n, sg.LOOKBACK)
        self.assertLess(abs(z), 3)


class SignalIds(unittest.TestCase):
    def test_the_same_signal_keeps_the_same_id(self):
        # A random id would multiply rows on every rebuild, and the outcome
        # attached to the old row would quietly describe a different claim.
        a = sg.signal_id("VRP", "2026-08-21", "NIFTY")
        b = sg.signal_id("VRP", "2026-08-21", "NIFTY")
        self.assertEqual(a, b)

    def test_different_signals_do_not_collide(self):
        ids = {sg.signal_id(f, "2026-08-21", "NIFTY", d)
               for f in ("VRP", "SKEW", "FLOW") for d in ("", "change", "spread")}
        self.assertEqual(len(ids), 9)


class NoLookahead(unittest.TestCase):
    """The one error that turns a research warehouse into a fiction."""

    def test_a_signal_ignores_days_at_or_after_its_own_date(self):
        today = state("2026-07-01")
        past = history(30)
        future = [state("2026-07-02", iv=99.0), state("2026-07-03", iv=99.0)]
        # Future rows are handed in deliberately; they must be discarded.
        built = sg.build_for_day(today, past + [today] + future)
        for s in built:
            self.assertLessEqual(s["history_days"], len(past))

    def test_a_signal_row_carries_no_forward_column(self):
        built = sg.build_for_day(state("2026-07-01"), history(30))
        forward = {"forward_realised_vol_5d", "variance_premium_5d",
                   "option_return_1d_pct", "underlying_return_1d_pct"}
        for s in built:
            self.assertEqual(forward & set(s), set())

    def test_an_outcome_only_looks_after_the_signal(self):
        sig = sg.build_for_day(state("2026-07-10"), history(30))[0]
        before = [state("2026-07-09", spot=99999.0)]
        after = [state(f"2026-07-{d}", spot=24000.0 + d * 10) for d in (11, 12, 13, 14, 15)]
        out = oc.build(sig, before + after)
        # If the earlier row leaked in, the return would be enormous.
        self.assertLess(abs(out["underlying_return_1d_pct"]), 10)


class Outcomes(unittest.TestCase):
    def _sig(self):
        return sg.build_for_day(state("2026-07-10", spot=24000.0, iv=12.0),
                                history(30))[0]

    def test_returns_are_measured_from_the_entry(self):
        after = [state(f"2026-07-{d}", spot=24240.0) for d in (11, 12, 13, 14, 15)]
        out = oc.build(self._sig(), after)
        self.assertAlmostEqual(out["underlying_return_1d_pct"], 1.0, places=2)

    def test_the_variance_premium_lives_here_and_only_here(self):
        after = [state(f"2026-07-{d}", spot=24000.0 * (1.01 ** i))
                 for i, d in enumerate((11, 12, 13, 14, 15), 1)]
        out = oc.build(self._sig(), after)
        self.assertIsNotNone(out["forward_realised_vol_5d"])
        self.assertIsNotNone(out["variance_premium_5d"])

    def test_an_unelapsed_horizon_reports_what_it_had(self):
        # Not a shorter window silently relabelled.
        out = oc.build(self._sig(), [state("2026-07-11", spot=24100.0)])
        self.assertEqual(out["horizon_days_available"], 1)
        self.assertIsNone(out["underlying_return_5d_pct"])

    def test_every_outcome_is_labelled_a_mark_not_a_fill(self):
        # Bhavcopy has no bid or ask. A return that has not paid a spread is
        # not alpha, and the label travels with the row rather than sitting in
        # documentation.
        after = [state(f"2026-07-{d}") for d in (11, 12, 13, 14, 15)]
        out = oc.build(self._sig(), after)
        self.assertEqual(out["return_basis"], "eod_mark")

    def test_no_days_after_means_no_outcome_row(self):
        self.assertIsNone(oc.build(self._sig(), []))


class Families(unittest.TestCase):
    def test_the_expected_families_are_produced(self):
        built = sg.build_for_day(state("2026-07-01"), history(30))
        self.assertEqual({s["signal_family"] for s in built},
                         {"VRP", "SKEW", "FLOW", "REGIME"})

    def test_a_disagreeing_skew_day_is_flagged_on_every_signal(self):
        built = sg.build_for_day(state("2026-07-01", agree=0.1), history(30))
        self.assertTrue(all("expiries_disagree_on_skew" in s["quality_flags"]
                            for s in built))

    def test_a_missing_measurement_produces_no_signal_rather_than_a_zero(self):
        thin = state("2026-07-01")
        thin["risk_reversal_30d"] = None
        built = sg.build_for_day(thin, history(30))
        self.assertNotIn("SKEW", {s["signal_family"] for s in built})


if __name__ == "__main__":
    unittest.main()


class ZeroIsAMeasurement(unittest.TestCase):
    """A calm market is not a missing market."""

    def test_a_zero_realised_volatility_still_yields_a_premium(self):
        # A market that did not move has zero volatility, and zero is falsy.
        # Truthiness treated it as missing, silently dropping the calmest days --
        # precisely the ones where implied volatility looks most expensive, and
        # so exactly the days a variance-premium study most needs.
        sig = sg.build_for_day(state("2026-07-10", iv=12.0, spot=24000.0),
                               history(30))[0]
        flat = [state(f"2026-07-{d}", spot=24000.0) for d in (11, 12, 13, 14, 15)]
        out = oc.build(sig, flat)
        self.assertEqual(out["forward_realised_vol_5d"], 0.0)
        self.assertIsNotNone(out["variance_premium_5d"])
        self.assertAlmostEqual(out["variance_premium_5d"], 12.0, places=2)

    def test_a_steadily_trending_market_is_not_called_calm(self):
        # The estimator assumes zero drift, so a market rising one percent a day
        # is moving, not still. The mean-subtracting version called this zero
        # volatility, which would price a persistent trend as a dead market.
        sig = sg.build_for_day(state("2026-07-10", iv=12.0, spot=24000.0),
                               history(30))[0]
        trending = [state(f"2026-07-{d}", spot=24000.0 * (1.01 ** i))
                    for i, d in enumerate((11, 12, 13, 14, 15), 1)]
        out = oc.build(sig, trending)
        self.assertGreater(out["forward_realised_vol_5d"], 5.0)

    def test_an_unchanged_implied_volatility_records_a_zero_change(self):
        sig = sg.build_for_day(state("2026-07-10", iv=12.0), history(30))[0]
        flat = [state(f"2026-07-{d}", iv=12.0) for d in (11, 12, 13, 14, 15)]
        out = oc.build(sig, flat)
        self.assertEqual(out["iv_change_1d"], 0.0)
        self.assertIsNotNone(out["iv_change_5d"])


class RebuildReplaces(unittest.TestCase):
    """A rebuild must not leave the previous definition behind.

    When the realised-volatility window was corrected, VRP correctly stopped
    producing on days it should never have produced on: 344 signals became 329.
    The upsert updated 329 rows and left 15 untouched, and the studies then read
    344 -- two definitions mixed into one result, reported as one.
    """

    def _run(self, *, dry_run):
        from options_lab import canonical_store as cs
        calls = []

        def fake_call(method, path, **kw):
            calls.append((method, path))
            if method == "GET" and cs.STATE_TABLE in path:
                return [dict(state(f"2026-07-{d:02d}"), spot=24000.0 + d)
                        for d in range(1, 29)]
            if method == "GET":
                return [{"signal_id": "old-one"}]
            return None

        with mock.patch.object(cs, "_call", side_effect=fake_call):
            out = sg.build_range("2026-07-10", "2026-07-20", dry_run=dry_run)
        return out, calls

    def test_a_real_rebuild_clears_the_range_first(self):
        out, calls = self._run(dry_run=False)
        deletes = [p for m, p in calls if m == "DELETE"]
        self.assertTrue(deletes, "the range must be cleared before writing")
        self.assertIn("observation_date=gte.2026-07-10", deletes[0])
        self.assertIn("observation_date=lte.2026-07-20", deletes[0])

    def test_the_delete_precedes_the_write(self):
        out, calls = self._run(dry_run=False)
        order = [m for m, p in calls if m in ("DELETE", "POST")]
        self.assertEqual(order[0], "DELETE")

    def test_it_reports_how_many_it_replaced(self):
        out, _ = self._run(dry_run=False)
        self.assertIn("replaced", out)

    def test_a_dry_run_deletes_nothing(self):
        out, calls = self._run(dry_run=True)
        self.assertEqual([p for m, p in calls if m == "DELETE"], [])
