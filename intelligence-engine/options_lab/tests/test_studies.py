"""Studies, and what they refuse to claim."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from options_lab import studies as st


def row(family, z, outcome, *, agree=1.0, field="variance_premium_5d"):
    return {"signal_family": family, "signal_zscore": z, field: outcome,
            "skew_agreement": agree, "return_basis": "eod_mark"}


class Buckets(unittest.TestCase):
    def test_z_scores_land_in_the_expected_bucket(self):
        for z, want in ((-3, "z <= -2"), (-1.5, "-2 to -1"), (0, "-1 to +1"),
                        (1.5, "+1 to +2"), (3, "z >= +2"), (None, "no_zscore")):
            self.assertEqual(st._bucket(z), want)

    def test_a_signal_without_a_zscore_is_kept_and_labelled(self):
        # Dropping them would quietly exclude the earliest days of any history,
        # which is a period, not a random sample.
        out = st.run([row("VRP", None, 1.0)], family="VRP",
                     outcome_field="variance_premium_5d")
        self.assertIn("no_zscore", out["buckets"])


class Honesty(unittest.TestCase):
    def test_a_thin_bucket_carries_a_warning_beside_its_mean(self):
        rows = [row("VRP", -3, 5.0) for _ in range(4)]
        out = st.run(rows, family="VRP", outcome_field="variance_premium_5d")
        self.assertIn("warning", out["buckets"]["z <= -2"])
        self.assertIn("4", out["buckets"]["z <= -2"]["warning"])

    def test_no_study_reports_a_p_value(self):
        rows = [row("VRP", -3, 5.0) for _ in range(30)] + \
               [row("VRP", 0, 1.0) for _ in range(30)]
        out = st.run(rows, family="VRP", outcome_field="variance_premium_5d")
        self.assertNotIn("p_value", str(out))
        self.assertNotIn("significant", str(out).lower())

    def test_a_small_difference_reads_as_noise(self):
        rows = [row("VRP", -3, 1.05) for _ in range(20)] + \
               [row("VRP", 0, 1.0) for _ in range(20)]
        out = st.run(rows, family="VRP", outcome_field="variance_premium_5d")
        self.assertIn("noise", out["tails_vs_middle"]["cheap"]["reading"])

    def test_a_large_separation_asks_for_more_data_not_a_conclusion(self):
        rows = [row("VRP", -3, 10.0 + i * 0.1) for i in range(20)] + \
               [row("VRP", 0, 1.0 + i * 0.1) for i in range(20)]
        out = st.run(rows, family="VRP", outcome_field="variance_premium_5d")
        self.assertEqual(out["tails_vs_middle"]["cheap"]["reading"],
                         "worth a larger sample")

    def test_the_return_basis_travels_into_the_result(self):
        # A study that dropped the label would report alpha it never measured.
        out = st.run([row("VRP", -3, 5.0)], family="VRP",
                     outcome_field="variance_premium_5d")
        self.assertEqual(out["return_basis"], "eod_mark")

    def test_run_all_states_that_these_are_marks(self):
        out = st.run_all([row("VRP", -3, 5.0)])
        self.assertIn("not tradeable", out["note"])


class Filtering(unittest.TestCase):
    def test_a_skew_study_can_exclude_days_the_expiries_disagreed_on(self):
        rows = [row("SKEW", -3, 1.0, agree=1.0, field="underlying_return_5d_pct"),
                row("SKEW", -3, 9.0, agree=0.1, field="underlying_return_5d_pct")]
        out = st.run(rows, family="SKEW",
                     outcome_field="underlying_return_5d_pct",
                     require_agreement=True)
        self.assertEqual(out["excluded_for_low_skew_agreement"], 1)
        self.assertEqual(out["buckets"]["z <= -2"]["n"], 1)

    def test_other_families_are_not_mixed_in(self):
        rows = [row("VRP", -3, 5.0), row("SKEW", -3, 99.0)]
        out = st.run(rows, family="VRP", outcome_field="variance_premium_5d")
        self.assertEqual(out["signals"], 1)

    def test_a_missing_outcome_is_skipped_not_counted_as_zero(self):
        rows = [row("VRP", -3, None), row("VRP", -3, 4.0)]
        out = st.run(rows, family="VRP", outcome_field="variance_premium_5d")
        self.assertEqual(out["buckets"]["z <= -2"]["n"], 1)
        self.assertEqual(out["buckets"]["z <= -2"]["mean"], 4.0)


if __name__ == "__main__":
    unittest.main()
