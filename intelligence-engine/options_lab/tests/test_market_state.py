"""Daily options market state, and the lookahead it must never contain."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import market_state as ms


def obs(strike, kind, *, oi=1000, vol=100, doi=0, dte=7, spot=24252.0,
        day="2026-08-21", expiry="2026-08-28"):
    return {"observation_date": day, "underlying_symbol": "NIFTY", "expiry": expiry,
            "strike": float(strike), "option_type": kind, "dte_days": dte,
            "open_interest": oi, "volume": vol, "change_open_interest": doi,
            "underlying_spot": spot}


def surface(dte, atm, rr, *, points=60, quality="high", expiry="2026-08-28"):
    return {"expiry": expiry, "dte_days": dte, "atm_iv": atm, "risk_reversal": rr,
            "butterfly": 0.2, "fit_points": points, "surface_quality": quality}


class MaxPain(unittest.TestCase):
    def test_pain_is_least_where_the_open_interest_sits(self):
        book = [obs(24000, "CE", oi=1000), obs(24000, "PE", oi=1000),
                obs(23900, "CE", oi=1), obs(24100, "PE", oi=1)]
        self.assertEqual(ms.max_pain(book)["max_pain"], 24000.0)

    def test_it_settles_between_a_call_wall_and_a_put_wall(self):
        book = [obs(24500, "CE", oi=900000), obs(24000, "CE", oi=100000),
                obs(23500, "PE", oi=900000), obs(24000, "PE", oi=100000)]
        out = ms.max_pain(book)
        self.assertEqual(out["max_pain"], 24000.0)
        self.assertEqual(out["peak_call_oi_strike"], 24500.0)
        self.assertEqual(out["peak_put_oi_strike"], 23500.0)
        self.assertAlmostEqual(out["call_oi_concentration"], 0.9, places=3)

    def test_a_chain_too_thin_to_describe_gets_no_max_pain(self):
        self.assertIsNone(ms.max_pain([obs(24000, "CE"), obs(24000, "PE")]))


class Ratios(unittest.TestCase):
    def test_a_ratio_with_no_calls_is_none_not_infinity(self):
        # Returning a number here would put an outlier in every percentile
        # that follows.
        self.assertIsNone(ms._ratio(500, 0))

    def test_a_normal_ratio_is_puts_over_calls(self):
        self.assertAlmostEqual(ms._ratio(120, 100), 1.2, places=4)


class RealisedVol(unittest.TestCase):
    def test_a_constant_growth_path_has_no_volatility(self):
        closes = [(f"d{i}", 100 * 1.01 ** i) for i in range(25)]
        self.assertLess(ms.realised_vols(closes)["realised_vol_20d"], 0.01)

    def test_too_short_a_history_yields_none_not_a_small_number(self):
        # A 20-day statistic from four closes is a different statistic wearing
        # the same name.
        out = ms.realised_vols([("d0", 100.0), ("d1", 101.0)])
        self.assertIsNone(out["realised_vol_5d"])


class ThirtyDayPoint(unittest.TestCase):
    def test_it_interpolates_between_the_bracketing_expiries(self):
        got = ms._thirty_day_point([surface(20, 9.0, -1.0), surface(40, 11.0, -2.0)])
        self.assertEqual(got["dte_days"], 30)
        self.assertAlmostEqual(got["atm_iv"], 10.0, places=3)
        self.assertAlmostEqual(got["risk_reversal"], -1.5, places=3)

    def test_a_thin_expiry_is_dropped_before_interpolating(self):
        # NIFTY lists monthlies that barely trade beside the weeklies.
        thin = surface(31, 9.0, +5.0, points=4)
        got = ms._thirty_day_point([surface(20, 9.0, -1.0, points=60), thin,
                                    surface(40, 11.0, -2.0, points=60)])
        self.assertLess(got["risk_reversal"], 0)

    def test_it_does_not_extrapolate_past_the_listed_expiries(self):
        got = ms._thirty_day_point([surface(90, 12.0, -2.0), surface(120, 13.0, -2.5)])
        self.assertEqual(got["dte_days"], 90)


class Build(unittest.TestCase):
    def _rows(self):
        rows = []
        for strike in range(23800, 24800, 100):
            rows += [obs(strike, "CE", oi=5000, vol=200),
                     obs(strike, "PE", oi=6000, vol=250)]
        return rows

    def test_disagreeing_expiries_are_reported_not_smoothed_away(self):
        # One expiry with the opposite skew sign must leave a trace. Filtering
        # until the data matches the expected direction is how a method gets
        # fitted to its own prior.
        surfaces = [surface(10, 9.0, -1.0), surface(25, 9.5, -1.2),
                    surface(32, 9.6, +4.0), surface(60, 10.0, -1.5)]
        st = ms.build(self._rows(), surfaces,
                      [(f"d{i}", 24000 + i * 10.0) for i in range(25)])
        self.assertIsNotNone(st["skew_agreement"])
        self.assertLess(st["skew_agreement"], 1.0)

    def test_agreeing_expiries_report_full_agreement(self):
        surfaces = [surface(10, 9.0, -1.0), surface(25, 9.5, -1.2),
                    surface(40, 9.8, -1.4)]
        st = ms.build(self._rows(), surfaces,
                      [(f"d{i}", 24000 + i * 10.0) for i in range(25)])
        self.assertEqual(st["skew_agreement"], 1.0)

    def test_the_row_carries_no_column_computed_from_a_later_date(self):
        # The variance risk premium against forward realised volatility is the
        # more useful number and is deliberately absent: a study conditioned on
        # it would find an edge nobody could have traded.
        st = ms.build(self._rows(), [surface(30, 9.5, -1.2)],
                      [(f"d{i}", 24000 + i * 10.0) for i in range(25)])
        for banned in ("forward_rv", "realised_vol_next_5d", "variance_premium"):
            self.assertNotIn(banned, st)
        self.assertIn("iv_minus_trailing_rv", st)

    def test_positioning_ignores_far_dated_open_interest(self):
        # A December strike says nothing about this week, and pooling it
        # flatters every concentration measure.
        near = self._rows()
        far = [obs(30000, "CE", oi=9_000_000, dte=300, expiry="2027-06-24")]
        with_far = ms.build(near + far, [surface(30, 9.5, -1.2)],
                            [(f"d{i}", 24000 + i * 10.0) for i in range(25)])
        self.assertNotEqual(with_far["peak_call_oi_strike"], 30000.0)

    def test_no_observations_is_no_state(self):
        self.assertIsNone(ms.build([], [surface(30, 9.5, -1.2)], []))


if __name__ == "__main__":
    unittest.main()


class SelectCoversWhatIsRead(unittest.TestCase):
    """The bug that left spot null on fifty-nine days without erroring.

    build() read o["underlying_spot"], and the query that fetches those rows
    never selected it. PostgREST does not object to a column you did not ask
    for -- the rows arrive, the key is absent, .get returns None, and every
    number built from it is null. Nothing fails, so nothing tells you.
    """

    def _selected(self) -> set:
        import re
        from pathlib import Path
        src = Path(__file__).resolve().parents[1].joinpath("canonical_store.py").read_text()
        block = src[src.index("def observations_for_day"):src.index("def upsert_surfaces")]
        cols = re.findall(r'"([a-z_,]+)"', block[block.index("cols = ("):block.index("query =")])
        return {c for chunk in cols for c in chunk.split(",") if c}

    def test_every_column_market_state_reads_is_selected(self):
        import re
        from pathlib import Path
        src = Path(__file__).resolve().parents[1].joinpath("market_state.py").read_text()
        read = set(re.findall(r'\.get\("([a-z_]+)"', src))
        read |= set(re.findall(r'row\["([a-z_]+)"\]', src))
        read |= set(re.findall(r'total\([a-z]+, "([a-z_]+)"\)', src))
        read |= set(re.findall(r'o\["([a-z_]+)"\]', src))
        # only the columns that come from an observation row
        from_observation = read & {
            "observation_date", "underlying_symbol", "expiry", "strike",
            "option_type", "dte_days", "implied_volatility", "iv_quality",
            "forward", "forward_quality", "underlying_spot", "volume",
            "open_interest", "change_open_interest"}
        missing = from_observation - self._selected()
        self.assertEqual(missing, set(),
                         f"market_state reads {sorted(missing)} but the query does "
                         f"not select them; they will silently be None")

    def test_spot_and_the_positioning_columns_are_selected(self):
        # Named explicitly so a future trim of the select fails here loudly.
        for column in ("underlying_spot", "open_interest", "volume",
                       "change_open_interest"):
            self.assertIn(column, self._selected())


class RealisedVolWindow(unittest.TestCase):
    """A twenty-day number must be built from twenty days."""

    def _closes(self, n):
        return [(f"d{i}", 100 * (1 + 0.01 * ((-1) ** i))) for i in range(n)]

    def test_a_short_window_is_null_not_a_smaller_number(self):
        # The first week of the warehouse reported rv20 of 4.65 and 4.95 from
        # three returns, where every later day sat between 8.9 and 13.5. Half
        # the true level, wearing the right label, and it inflated the whole
        # implied-minus-realised series.
        self.assertIsNone(realised := ms.realised_vols(self._closes(8))["realised_vol_20d"])

    def test_the_five_day_window_fills_long_before_the_twenty(self):
        out = ms.realised_vols(self._closes(8))
        self.assertIsNotNone(out["realised_vol_5d"])
        self.assertIsNone(out["realised_vol_20d"])

    def test_a_filled_window_measures(self):
        out = ms.realised_vols(self._closes(25))
        self.assertIsNotNone(out["realised_vol_20d"])
        self.assertGreater(out["realised_vol_20d"], 0)

    def test_a_short_window_never_reads_lower_than_the_full_one(self):
        # The failure mode was directional: too few returns understated
        # volatility, which overstated every premium built on it.
        full = ms.realised_vols(self._closes(25))["realised_vol_20d"]
        self.assertIsNone(ms.realised_vols(self._closes(10))["realised_vol_20d"],
                          "a partial window must not report a number at all")
        self.assertIsNotNone(full)
