"""Fitting a smile, and refusing to fit noise."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import surfaces as sf


F = 24287.0
DTE = 7


def chain(level=12.0, slope=-8.0, curve=60.0, *, dte=DTE, strikes=None,
          extra=None):
    """A chain priced from a known smile, in log-moneyness.

    Strikes are 50 apart as NSE actually lists them on NIFTY, roughly 0.2% of
    spot. Spacing matters to these tests: the fit band scales with sigma*sqrt(T),
    so a coarse grid leaves a near expiry with too few points to fit -- which is
    a real property of the fitter, not something a fixture should paper over.
    """
    strikes = strikes or [F - (F % 50) + 50 * i for i in range(-60, 61)]
    rows = []
    for strike in strikes:
        k = math.log(strike / F)
        iv = level + slope * k + curve * k * k
        for kind in ("CE", "PE"):
            rows.append(row(strike, kind, iv, dte=dte))
    return rows + (extra or [])


def row(strike, kind, iv, *, dte=DTE):
    return {"observation_date": "2026-08-21", "underlying_symbol": "NIFTY",
            "expiry": "2026-08-28", "dte_days": dte, "strike": float(strike),
            "option_type": kind, "implied_volatility": iv, "iv_quality": "ok",
            "forward": F, "forward_quality": "high"}


class Fitting(unittest.TestCase):
    def test_a_known_smile_comes_back(self):
        s = sf.fit_expiry(chain(level=12.0, slope=-8.0))
        self.assertAlmostEqual(s["atm_iv"], 12.0, delta=0.15)
        self.assertAlmostEqual(s["atm_slope"], -8.0, delta=1.0)
        self.assertLess(s["fit_rmse"], 0.1)

    def test_the_quadratic_solver_is_exact(self):
        xs = [-0.2, -0.1, 0.0, 0.1, 0.2]
        a, b, c = sf._quadratic_fit(xs, [12 + 3 * x + 40 * x * x for x in xs])
        self.assertAlmostEqual(a, 12.0, places=6)
        self.assertAlmostEqual(b, 3.0, places=6)
        self.assertAlmostEqual(c, 40.0, places=6)

    def test_puts_richer_than_calls_reads_as_negative_skew(self):
        # The equity index direction. Getting the sign backwards would invert
        # every skew study built on this column.
        s = sf.fit_expiry(chain(slope=-20.0))
        self.assertLess(s["risk_reversal"], 0)


class RefusingNoise(unittest.TestCase):
    def test_worthless_wings_do_not_drag_the_fit(self):
        # Real chains carry deep out-of-the-money contracts trading at thirty
        # paise whose solved volatility is 255% against an at-the-money 8%.
        # Three of those once produced a negative at-the-money volatility.
        junk = [row(F * 1.03, "CE", 254.9), row(F * 1.035, "CE", 255.2),
                row(F * 1.04, "CE", 253.0)]
        s = sf.fit_expiry(chain(level=8.0, extra=junk))
        self.assertIsNotNone(s)
        self.assertAlmostEqual(s["atm_iv"], 8.0, delta=0.5)
        self.assertGreater(s["atm_iv"], 0)

    def test_one_stale_quote_is_dropped_by_the_refit(self):
        # Inside the band and inside the plausible range, so only a residual
        # betrays it.
        s = sf.fit_expiry(chain(level=12.0) + [row(F * 1.005, "CE", 19.0)])
        self.assertAlmostEqual(s["atm_iv"], 12.0, delta=0.3)

    def test_a_surface_that_agrees_with_its_own_nonsense_is_still_refused(self):
        # The relative bound is measured against a median of near-money points,
        # so a chain where those are themselves nonsense fits cleanly and
        # reports 300% at the money with an rmse of zero. An index does not
        # trade there, and nothing liquid enough to fit does.
        wild = [row(F * (1 + 0.001 * i), "CE", 8.0 if i % 2 else 300.0)
                for i in range(-10, 11)]
        self.assertIsNone(sf.fit_expiry(wild))

    def test_a_negative_fitted_volatility_is_refused_not_graded(self):
        # What three 255% wings once did to a real front-month chain.
        junk = [row(F * (1 + 0.02 + 0.002 * i), "CE", 250.0) for i in range(6)]
        s = sf.fit_expiry(chain(level=8.0, extra=junk))
        if s is not None:
            self.assertGreater(s["atm_iv"], 0)

    def test_too_few_points_is_no_surface(self):
        self.assertIsNone(sf.fit_expiry(chain(strikes=[F, F * 1.01])))


class BandScaling(unittest.TestCase):
    def test_the_band_is_narrower_in_strike_terms_for_a_near_expiry(self):
        # A fixed log-moneyness band is 31 standard deviations wide on a
        # four-day expiry and barely two on a one-year one.
        near = sf.fit_expiry(chain(dte=4))
        far = sf.fit_expiry(chain(dte=365))
        self.assertIsNotNone(near)
        self.assertIsNotNone(far)
        self.assertLess(near["fit_points"], far["fit_points"])

    def test_in_the_money_options_are_not_fitted(self):
        # Mostly intrinsic value, so the price says little about volatility.
        deep = [row(F * 0.80, "CE", 60.0), row(F * 1.20, "PE", 60.0)]
        s = sf.fit_expiry(chain(level=12.0, extra=deep))
        self.assertAlmostEqual(s["atm_iv"], 12.0, delta=0.3)


class Day(unittest.TestCase):
    def test_each_expiry_gets_its_own_surface(self):
        rows = chain(dte=7)
        later = [dict(r, expiry="2026-09-28", dte_days=38) for r in chain(dte=38)]
        out = sf.fit_day(rows + later)
        self.assertEqual(len(out), 2)
        self.assertEqual({s["expiry"] for s in out}, {"2026-08-28", "2026-09-28"})

    def test_an_unfittable_expiry_is_skipped_not_faked(self):
        out = sf.fit_day(chain() + [row(F, "CE", 12.0, dte=99)
                                    | {"expiry": "2026-11-28"}])
        self.assertEqual([s["expiry"] for s in out], ["2026-08-28"])


if __name__ == "__main__":
    unittest.main()
