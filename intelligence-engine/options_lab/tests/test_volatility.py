"""The estimator that decides how large every premium looks."""

from __future__ import annotations

import math
import random
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import volatility as vol


class BiasFactor(unittest.TestCase):
    def test_it_shrinks_toward_one_as_the_window_grows(self):
        # Which is why the error hides in short windows and only shows itself
        # when a five-day number sits beside a twenty-day one.
        factors = [vol._bias_factor(n) for n in (3, 5, 10, 20, 60)]
        self.assertEqual(factors, sorted(factors))
        self.assertLess(factors[0], 0.93)
        self.assertGreater(factors[-1], 0.99)

    def test_a_large_window_does_not_overflow(self):
        self.assertAlmostEqual(vol._bias_factor(500), 1.0, places=2)


class Unbiased(unittest.TestCase):
    def test_five_returns_no_longer_understate_volatility(self):
        # The whole point. A population standard deviation over five returns
        # reads about sixteen percent low, and the error runs one way, so every
        # premium measured against it is inflated.
        random.seed(3)
        true = 0.0057
        truth = true * math.sqrt(252) * 100
        old, new = [], []
        for _ in range(20000):
            r = [random.gauss(0, true) for _ in range(5)]
            old.append(statistics.pstdev(r) * math.sqrt(252) * 100)
            new.append(vol.annualised(r))
        self.assertLess(statistics.mean(old), truth * 0.90)
        self.assertAlmostEqual(statistics.mean(new) / truth, 1.0, delta=0.03)

    def test_twenty_returns_are_close_either_way(self):
        random.seed(5)
        true = 0.0057
        r = [[random.gauss(0, true) for _ in range(20)] for _ in range(5000)]
        corrected = statistics.mean(vol.annualised(x) for x in r)
        self.assertAlmostEqual(corrected / (true * math.sqrt(252) * 100), 1.0,
                               delta=0.03)


class Edges(unittest.TestCase):
    def test_a_flat_series_is_zero_not_none(self):
        # Zero is a measurement. Returning None would drop the calmest days.
        self.assertEqual(vol.annualised([0.0, 0.0, 0.0, 0.0]), 0.0)

    def test_too_few_returns_gives_nothing(self):
        self.assertIsNone(vol.annualised([0.01, -0.01]))

    def test_a_steady_trend_registers_as_movement(self):
        # Zero drift is assumed, so a market rising every day is moving. The
        # mean-subtracting estimator called this still, which would price a
        # persistent trend as a dead market.
        self.assertGreater(vol.annualised([0.01] * 5), 5.0)

    def test_non_finite_returns_are_dropped_not_propagated(self):
        self.assertIsNotNone(vol.annualised([0.01, float("nan"), -0.01, 0.02, 0.01]))


class LogReturns(unittest.TestCase):
    def test_a_doubling_is_ln_two(self):
        self.assertAlmostEqual(vol.log_returns([100.0, 200.0])[0], math.log(2), places=9)

    def test_a_zero_or_negative_price_is_skipped(self):
        self.assertEqual(len(vol.log_returns([100.0, 0.0, 110.0, 120.0])), 1)


if __name__ == "__main__":
    unittest.main()
