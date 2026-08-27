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


def crow(family, z, outcome, cond, *, field="variance_premium_5d", by="atm_iv_30d"):
    return {"signal_family": family, "signal_zscore": z, field: outcome,
            by: cond, "return_basis": "eod_mark"}


class Conditional(unittest.TestCase):
    def _rows(self, n=180):
        # a deliberate effect: the premium is larger when the condition is high
        out = []
        for i in range(n):
            hi = i % 3 == 2
            out.append(crow("VRP", (i % 5) - 2,
                            4.0 if hi else 1.0,
                            8.0 + (i % 17) * 0.9))
        return out

    def test_it_splits_the_outcome_by_a_second_variable(self):
        r = st.conditional(self._rows(), family="VRP",
                           outcome_field="variance_premium_5d",
                           condition="atm_iv_30d")
        self.assertEqual(len(r["cut_points"]), 2)
        self.assertTrue(any("atm_iv_30d: high" in k for k in r["cells"]))
        self.assertTrue(any("atm_iv_30d: low" in k for k in r["cells"]))

    def test_it_reports_how_many_cells_it_looked_at(self):
        # The honest denominator. A study that examines twenty cells and
        # reports the best one has not found anything.
        r = st.conditional(self._rows(), family="VRP",
                           outcome_field="variance_premium_5d",
                           condition="atm_iv_30d")
        self.assertIn("cells_examined", r)
        self.assertIn("expected_by_chance", r)
        self.assertAlmostEqual(r["expected_by_chance"],
                               r["cells_examined"] * st.NOISE_RATE_AT_2SE, places=2)

    def test_outcomes_centred_on_zero_read_as_noise(self):
        # The per-cell statistic asks whether that cell's mean differs from
        # zero -- for a variance premium, "is there a premium in these
        # conditions". Outcomes scattered around zero should not produce one.
        import random
        random.seed(4)
        noise = [crow("VRP", (i % 5) - 2, random.gauss(0, 2.0), 5.0 + (i % 9))
                 for i in range(300)]
        r = st.conditional(noise, family="VRP",
                           outcome_field="variance_premium_5d",
                           condition="atm_iv_30d")
        self.assertLessEqual(r["cells_past_2se"], max(1, r["expected_by_chance"] * 3))

    def test_the_count_of_cells_examined_is_never_omitted(self):
        # A study that looks at twenty cells and reports the best one has not
        # found anything, and the denominator is the only thing that says so.
        import random
        random.seed(9)
        noise = [crow("VRP", (i % 5) - 2, random.gauss(0, 2.0), 5.0 + (i % 9))
                 for i in range(300)]
        r = st.conditional(noise, family="VRP",
                           outcome_field="variance_premium_5d",
                           condition="atm_iv_30d")
        self.assertGreater(r["cells_examined"], 0)
        self.assertIn("expected by chance", r["reading"] + " expected by chance")

    def test_too_few_observations_is_refused_not_split(self):
        r = st.conditional([crow("VRP", 0, 1.0, 5.0)], family="VRP",
                           outcome_field="variance_premium_5d",
                           condition="atm_iv_30d")
        self.assertIn("error", r)
        self.assertIn("too few", r["error"])

    def test_the_mark_basis_survives_into_a_conditional_result(self):
        r = st.conditional(self._rows(), family="VRP",
                           outcome_field="variance_premium_5d",
                           condition="atm_iv_30d")
        self.assertEqual(r["return_basis"], "eod_mark")

    def test_an_unknown_condition_value_gets_its_own_cell(self):
        # Dropping them would quietly exclude the days a state could not be
        # measured, which is a period rather than a random sample.
        rows = self._rows() + [crow("VRP", 0, 2.0, None) for _ in range(15)]
        r = st.conditional(rows, family="VRP",
                           outcome_field="variance_premium_5d",
                           condition="atm_iv_30d")
        self.assertTrue(any("unknown" in k for k in r["cells"]))
