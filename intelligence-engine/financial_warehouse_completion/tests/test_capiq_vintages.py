"""Conventions in the Capital IQ vintage export that would corrupt a backtest.

Two are silent and would not raise anything:

* CIQ writes 0 for "no data". The estimate sheet contains 169,091 such cells
  against 48,349 real ones - treating them as data would put three fictitious
  zeros into every factor for every genuine observation.
* The workbook's period-end column returned "(Invalid Time Period)" throughout,
  so the fiscal year each FY1 refers to is derived rather than read. A derived
  label that silently claimed to be vendor-supplied would be worse than no
  label at all.
"""

from __future__ import annotations

from datetime import date

from financial_warehouse_completion import capiq_vintages as cv


class TestIdentifiers:
    def test_strips_the_capiq_isin_prefix(self):
        assert cv._clean_isin("I_INE144J01027") == "INE144J01027"

    def test_accepts_a_bare_isin(self):
        assert cv._clean_isin("INE466L01038") == "INE466L01038"

    def test_rejects_a_non_isin(self):
        assert cv._clean_isin("NOT_AN_ISIN") is None
        assert cv._clean_isin("") is None

    def test_strips_the_exchange_prefix_from_the_ticker(self):
        assert cv._clean_symbol("NSEI:20MICRONS") == "20MICRONS"
        assert cv._clean_symbol("BSE:RELIANCE") == "RELIANCE"

    def test_accepts_a_bare_ticker(self):
        assert cv._clean_symbol("RELIANCE") == "RELIANCE"


class TestZeroSentinel:
    def test_zero_is_missing_not_a_forecast(self):
        """The single most damaging convention in this export."""
        assert cv._number(0) is None
        assert cv._number(0.0) is None
        assert cv._number("0") is None

    def test_invalid_time_period_is_missing(self):
        assert cv._number("(Invalid Time Period)") is None

    def test_real_values_survive_including_negatives(self):
        assert cv._number(10.3781) == 10.3781
        assert cv._number(-30.55429) == -30.55429  # loss-making names are real

    def test_blank_and_garbage_are_missing(self):
        for bad in (None, "", "   ", "n/a", True):
            assert cv._number(bad) is None


class TestFiscalPeriodDerivation:
    """Indian fiscal years end 31 March."""

    def test_january_forward_estimate_points_at_the_current_fy(self):
        label, end = cv.fiscal_period(date(2020, 1, 31), forward=True)
        assert label == "FY2020"
        assert end == date(2020, 3, 31)

    def test_april_forward_estimate_rolls_to_the_next_fy(self):
        label, end = cv.fiscal_period(date(2020, 4, 30), forward=True)
        assert label == "FY2021"
        assert end == date(2021, 3, 31)

    def test_the_roll_happens_between_march_and_april(self):
        assert cv.fiscal_period(date(2023, 3, 31), forward=True)[0] == "FY2023"
        assert cv.fiscal_period(date(2023, 4, 1), forward=True)[0] == "FY2024"

    def test_reported_figures_refer_to_the_completed_year(self):
        """An actual known in Jan 2020 is for the year ended March 2019."""
        assert cv.fiscal_period(date(2020, 1, 31), forward=False)[0] == "FY2019"
        assert cv.fiscal_period(date(2020, 4, 30), forward=False)[0] == "FY2020"

    def test_forward_is_always_one_year_ahead_of_reported(self):
        for month in (1, 3, 4, 7, 12):
            d = date(2022, month, 15)
            fwd = int(cv.fiscal_period(d, forward=True)[0][2:])
            rep = int(cv.fiscal_period(d, forward=False)[0][2:])
            assert fwd - rep == 1


class TestRowContract:
    def test_derived_period_is_labelled_as_derived(self):
        """A derived label must never be mistaken for a vendor-supplied one."""
        parsed = cv.parse()
        if not parsed.get("rows"):
            return  # workbook absent in this checkout
        row = parsed["rows"][0]
        assert row["period_source"] == "derived_indian_fy"

    def test_estimates_and_actuals_are_distinguishable(self):
        parsed = cv.parse()
        rows = parsed.get("rows") or []
        if not rows:
            return
        metrics = {r["metric"] for r in rows}
        assert "eps_estimate" in metrics or "eps_reported" in metrics
        for r in rows[:200]:
            expected = "true" if r["metric"] == "eps_estimate" else "false"
            assert r["is_forward_estimate"] == expected

    def test_no_zero_values_reach_the_warehouse(self):
        parsed = cv.parse()
        for r in (parsed.get("rows") or [])[:5000]:
            assert r["mean_estimate"] != 0

    def test_grain_matches_the_warehouse_key(self):
        """Tab keys on (symbol, consensus_date, target_period, metric)."""
        parsed = cv.parse()
        rows = (parsed.get("rows") or [])[:20000]
        if not rows:
            return
        keys = {(r["symbol"], r["consensus_date"], r["target_period"], r["metric"])
                for r in rows}
        assert len(keys) == len(rows), "duplicate rows would collapse on insert"
