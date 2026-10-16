"""The AGI-versus-Street gap, and the joins that would silently corrupt it."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from situational_awareness import consensus_gap as cg


def street(symbol, period, stamp, value, metric="eps_estimate"):
    return {"symbol": symbol, "target_period": period, "consensus_date": stamp,
            "metric": metric, "mean_estimate": value}


def agi(symbol, period, stamp, value, *, scenario="base", conf=0.8):
    return {"symbol": symbol, "target_period": period, "forecast_as_of": stamp,
            "metric": "eps", "scenario": scenario, "forecast_value": value,
            "confidence_score": conf}


class PeriodLabels(unittest.TestCase):
    def test_the_two_warehouses_agree_after_normalising(self):
        """AGI writes FY27, Capital IQ writes FY2027. Raw, they never join."""
        self.assertEqual(cg.normalise_period("FY27"), "FY2027")
        self.assertEqual(cg.normalise_period("FY2027"), "FY2027")
        self.assertEqual(cg.normalise_period("2027"), "FY2027")
        self.assertEqual(cg.normalise_period("fy 27"), "FY2027")
        self.assertIsNone(cg.normalise_period(""))
        self.assertIsNone(cg.normalise_period("FY2027E"))

    def test_join_actually_produces_rows_across_the_label_mismatch(self):
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[agi("INFY", "FY27", "2026-08-17", 70.0)],
            street_rows=[street("INFY", "FY2027", "2026-08-19", 62.0)],
        )
        self.assertEqual(len(out["rows"]), 1)
        row = out["rows"][0]
        self.assertEqual(row["fiscal_period"], "FY2027")
        self.assertAlmostEqual(row["eps_gap_abs"], 8.0)
        self.assertAlmostEqual(row["eps_gap_pct"], 8.0 / 62.0 * 100.0, places=3)

    def test_different_fiscal_years_never_join(self):
        """FY2027 against FY2028 is a year of growth, not a disagreement."""
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[agi("INFY", "FY28", "2026-08-17", 80.0)],
            street_rows=[street("INFY", "FY2027", "2026-08-19", 62.0)],
        )
        self.assertEqual(out["rows"], [])


class PointInTime(unittest.TestCase):
    def test_a_later_vintage_is_not_visible(self):
        """A row dated June cannot read an August estimate."""
        out = cg.build_rows(
            date(2026, 6, 30),
            agi_rows=[agi("TCS", "FY27", "2026-06-01", 150.0)],
            street_rows=[street("TCS", "FY2027", "2026-05-31", 140.0),
                         street("TCS", "FY2027", "2026-08-19", 999.0)],
        )
        self.assertEqual(len(out["rows"]), 1)
        self.assertAlmostEqual(out["rows"][0]["street_eps"], 140.0)

    def test_ages_are_recorded_not_assumed(self):
        out = cg.build_rows(
            date(2026, 6, 30),
            agi_rows=[agi("TCS", "FY27", "2026-06-20", 150.0)],
            street_rows=[street("TCS", "FY2027", "2026-05-31", 140.0)],
        )
        row = out["rows"][0]
        self.assertEqual(row["agi_eps_age_days"], 10)
        self.assertEqual(row["street_eps_age_days"], 30)

    def test_stale_sides_are_dropped(self):
        out = cg.build_rows(
            date(2026, 6, 30),
            agi_rows=[agi("TCS", "FY27", "2020-01-01", 150.0)],
            street_rows=[street("TCS", "FY2027", "2026-05-31", 140.0)],
        )
        self.assertEqual(out["rows"], [])
        self.assertEqual(out["coverage"]["stale"], 1)


class Denominator(unittest.TestCase):
    def test_capiq_zero_sentinel_is_not_a_forecast(self):
        """Capital IQ writes 0 for no-data; dividing by it invents an infinity."""
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[agi("X", "FY27", "2026-08-17", 40.0)],
            street_rows=[street("X", "FY2027", "2026-08-19", 0.0)],
        )
        self.assertEqual(out["rows"], [])
        self.assertEqual(out["coverage"]["street_too_small"], 1)

    def test_a_tiny_street_estimate_does_not_dominate_the_ranking(self):
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[agi("X", "FY27", "2026-08-17", 1.0)],
            street_rows=[street("X", "FY2027", "2026-08-19", 0.02)],
        )
        self.assertEqual(out["rows"], [])

    def test_negative_street_eps_uses_absolute_denominator(self):
        """A loss-maker turning profitable is a positive gap, not a negative one."""
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[agi("X", "FY27", "2026-08-17", 2.0)],
            street_rows=[street("X", "FY2027", "2026-08-19", -4.0)],
        )
        row = out["rows"][0]
        self.assertAlmostEqual(row["eps_gap_abs"], 6.0)
        self.assertGreater(row["eps_gap_pct"], 0)


class SourceTagging(unittest.TestCase):
    def test_fallback_is_off_by_default(self):
        """Coverage is never padded silently."""
        out = cg.build_rows(
            date(2026, 8, 20), agi_rows=[],
            street_rows=[street("X", "FY2027", "2026-08-19", 10.0)],
        )
        self.assertEqual(out["rows"], [])

    def test_fallback_rows_are_tagged_and_kept_separable(self):
        reported = [street("X", f"FY202{i}", f"202{i}-06-30", 10.0 * (1.1 ** i),
                           metric="eps_reported") for i in range(1, 6)]
        out = cg.build_rows(
            date(2026, 8, 20), agi_rows=[],
            street_rows=[street("X", "FY2027", "2026-08-19", 10.0)] + reported,
            allow_fallback=True,
        )
        self.assertEqual(len(out["rows"]), 1)
        row = out["rows"][0]
        self.assertEqual(row["agi_eps_source"], cg.SOURCE_FALLBACK)
        self.assertLessEqual(row["forecast_confidence"], 0.35)
        self.assertEqual(out["coverage"]["fallback"], 1)
        self.assertEqual(out["coverage"]["modelled"], 0)

    def test_a_real_model_estimate_always_wins_over_the_formula(self):
        reported = [street("X", f"FY202{i}", f"202{i}-06-30", 10.0,
                           metric="eps_reported") for i in range(1, 6)]
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[agi("X", "FY27", "2026-08-17", 77.0)],
            street_rows=[street("X", "FY2027", "2026-08-19", 10.0)] + reported,
            allow_fallback=True,
        )
        row = out["rows"][0]
        self.assertEqual(row["agi_eps_source"], cg.SOURCE_MODEL)
        self.assertAlmostEqual(row["agi_eps"], 77.0)

    def test_cagr_is_measured_across_fiscal_years_not_vintage_dates(self):
        """All five years published on one day must still yield a growth rate."""
        rows = [street("X", f"FY202{i}", "2026-01-01", 10.0 * (1.1 ** i),
                       metric="eps_reported") for i in range(1, 6)]
        hist = cg.reported_by_symbol(rows, date(2026, 8, 20))
        made = cg.mechanical_eps(hist["X"], "FY2027")
        self.assertIsNotNone(made)
        self.assertGreater(made[0], hist["X"][2025])

    def test_a_loss_making_history_refuses_a_cagr(self):
        rows = [street("X", "FY2023", "2026-01-01", -5.0, metric="eps_reported"),
                street("X", "FY2024", "2026-01-01", 2.0, metric="eps_reported"),
                street("X", "FY2025", "2026-01-01", 4.0, metric="eps_reported")]
        hist = cg.reported_by_symbol(rows, date(2026, 8, 20))
        self.assertIsNone(cg.mechanical_eps(hist["X"], "FY2027"))


class RevisionControl(unittest.TestCase):
    def test_no_earlier_vintage_is_not_a_flat_revision(self):
        series = [(date(2026, 8, 19), 62.0)]
        self.assertIsNone(cg.street_revision_pct(series, date(2026, 8, 20)))

    def test_revision_is_measured_on_a_fixed_target_period(self):
        """Cutoff must land between the two vintages for a baseline to exist."""
        series = [(date(2026, 3, 31), 50.0), (date(2026, 8, 19), 55.0)]
        got = cg.street_revision_pct(series, date(2026, 8, 20), lookback_days=100)
        self.assertAlmostEqual(got, 10.0, places=3)

    def test_a_lookback_predating_all_history_yields_no_revision(self):
        """Reaching back past the first vintage is not a zero revision."""
        series = [(date(2026, 3, 31), 50.0), (date(2026, 8, 19), 55.0)]
        self.assertIsNone(
            cg.street_revision_pct(series, date(2026, 8, 20), lookback_days=300))


class FourStates(unittest.TestCase):
    def test_early_variant_perception(self):
        """Large positive gap, Street flat or falling: the interesting case."""
        self.assertEqual(cg.classify(18.0, -1.0), "early_variant_perception")
        self.assertEqual(cg.classify(18.0, 0.0), "early_variant_perception")

    def test_thesis_being_discovered(self):
        self.assertEqual(cg.classify(18.0, 14.0), "thesis_being_discovered")

    def test_consensus_momentum(self):
        self.assertEqual(cg.classify(3.0, 14.0), "consensus_momentum")

    def test_street_over_extrapolating(self):
        self.assertEqual(cg.classify(-18.0, 14.0), "street_may_be_over_extrapolating")

    def test_a_gap_without_revision_history_says_so(self):
        self.assertEqual(cg.classify(18.0, None), "gap_no_revision_history")


class GapConfidence(unittest.TestCase):
    def test_absent_causal_state_does_not_penalise_the_gap(self):
        self.assertAlmostEqual(cg._gap_confidence(0.8, None), 0.8)

    def test_causal_confidence_can_lower_but_never_raise(self):
        self.assertLess(cg._gap_confidence(0.8, 0.5), 0.8)
        self.assertLessEqual(cg._gap_confidence(0.8, 1.0), 0.8)

    def test_causal_fields_are_carried_when_present(self):
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[agi("NTPC", "FY27", "2026-08-17", 25.0)],
            street_rows=[street("NTPC", "FY2027", "2026-08-19", 20.0)],
            causal_impacts={"NTPC": {"exposure_effect_pct": 2.97,
                                     "exposure_effect_low": 1.2,
                                     "exposure_effect_high": 4.4,
                                     "confidence": 0.64}},
        )
        row = out["rows"][0]
        self.assertAlmostEqual(row["causal_exposure_effect_pct"], 2.97)
        self.assertAlmostEqual(row["causal_effect_low"], 1.2)
        self.assertAlmostEqual(row["causal_effect_high"], 4.4)
        self.assertEqual(out["coverage"]["with_causal_state"], 1)


if __name__ == "__main__":
    unittest.main()


class Provenance(unittest.TestCase):
    """A formula must not be able to present itself as a fundamental estimate."""

    def _extrapolated(self, **over):
        row = {"symbol": "X", "target_period": "FY28", "forecast_as_of": "2026-08-17",
               "metric": "eps", "scenario": "base", "horizon": "FY+2",
               "base_value": 433.42, "historical_cagr_pct": 19.39,
               "forecast_value": 617.76, "confidence_score": 1.0}
        row.update(over)
        return row

    def test_a_cagr_extrapolation_is_detected(self):
        """433.42 x 1.1939^2 = 617.7, which is what the row claims to forecast."""
        self.assertEqual(cg.agi_source_of(self._extrapolated()), cg.SOURCE_FALLBACK)

    def test_a_genuine_estimate_is_not_flagged(self):
        """A number the formula does not reproduce is a real judgement."""
        row = self._extrapolated(forecast_value=430.0)
        self.assertEqual(cg.agi_source_of(row), cg.SOURCE_MODEL)

    def test_missing_inputs_default_to_model(self):
        """Absent a formula to check against, do not accuse the row."""
        row = self._extrapolated(base_value=None)
        self.assertEqual(cg.agi_source_of(row), cg.SOURCE_MODEL)

    def test_extrapolated_rows_are_excluded_unless_fallback_is_enabled(self):
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[self._extrapolated()],
            street_rows=[street("X", "FY2028", "2026-08-19", 99.15)],
        )
        self.assertEqual(out["rows"], [])
        self.assertEqual(out["coverage"]["extrapolated_not_modelled"], 1)

    def test_extrapolated_rows_are_tagged_and_capped_when_allowed(self):
        out = cg.build_rows(
            date(2026, 8, 20),
            agi_rows=[self._extrapolated()],
            street_rows=[street("X", "FY2028", "2026-08-19", 99.15)],
            allow_fallback=True,
        )
        row = out["rows"][0]
        self.assertEqual(row["agi_eps_source"], cg.SOURCE_FALLBACK)
        # confidence_score was 1.0; a formula does not get to claim certainty.
        self.assertLessEqual(row["forecast_confidence"], 0.35)

    def test_rounding_at_small_eps_does_not_disguise_a_formula(self):
        """ETERNAL: 0.39 x 0.9938^2 = 0.3852, stored as 0.39 -- still a formula."""
        row = self._extrapolated(base_value=0.39, historical_cagr_pct=-0.62,
                                 forecast_value=0.39, horizon="FY+2")
        self.assertEqual(cg.agi_source_of(row), cg.SOURCE_FALLBACK)
