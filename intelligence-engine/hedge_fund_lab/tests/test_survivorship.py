"""Sizing the survivorship gap from the NSE delisted-companies list.

The list has no prices, so it cannot fix a backtest. It has names and dates,
which is enough to say how much of the past universe the warehouse cannot see -
a number nobody had, even approximately.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import survivorship as sv


def _row(symbol, delisted_on, reason="Compulsory Delisting"):
    return {"symbol": symbol, "delisted_on": delisted_on, "reason": reason,
            "category": sv.categorise(reason)}


class TestCategorise:
    def test_forced_exits_are_failures(self):
        """A shareholder in these usually loses most of the position."""
        assert sv.categorise("Compulsory Delisting") == "failure"
        assert sv.categorise("Delisting - Liquidation") == "failure"
        assert sv.categorise("Operation of Law") == "failure"

    def test_a_buyout_is_not_a_failure(self):
        """A voluntary delisting normally pays shareholders a premium, so
        counting it as a missing loss would overstate the bias."""
        assert sv.categorise("Voluntary Delisting") == "voluntary"
        assert sv.categorise("Exit from ITP platform") == "voluntary"

    def test_an_unknown_reason_is_never_assumed_to_be_a_failure(self):
        assert sv.categorise("Pursuant to gazette notification") == "other"
        assert sv.categorise("") == "other"
        assert sv.categorise(None) == "other"


class TestMissingAt:
    def test_a_company_still_trading_that_month_counts_as_missing(self):
        rows = [_row("DEADCO", "2021-06-15")]
        assert len(sv.missing_at("2020-03", rows)) == 1

    def test_a_company_already_gone_does_not(self):
        """It was not tradeable then, so the backtest was right not to see it."""
        rows = [_row("DEADCO", "2019-01-10")]
        assert sv.missing_at("2020-03", rows) == []

    def test_the_company_must_survive_to_the_ranking_date(self):
        """The backtest ranks at month end and holds to the next one, so a
        company delisted on 31 March could not have been bought that month.
        It counts as missing for February, not for March."""
        rows = [_row("DEADCO", "2020-03-31")]
        assert sv.missing_at("2020-03", rows) == [], "already gone at the March ranking"
        assert len(sv.missing_at("2020-02", rows)) == 1, "still listed at the February ranking"

    def test_a_malformed_month_returns_nothing(self):
        assert sv.missing_at("nonsense", [_row("A", "2021-01-01")]) == []


class TestBiasReport:
    def test_counts_the_gap_and_the_failures_within_it(self):
        rows = [_row("A", "2021-01-01"), _row("B", "2021-01-01"),
                _row("C", "2021-01-01", "Voluntary Delisting")]
        out = sv.bias_report({"2020-01": 97}, rows)
        period = out["periods"][0]
        assert period["missing"] == 3
        assert period["missing_failures"] == 2, "the voluntary exit is not a failure"
        assert period["estimated_true_universe"] == 100
        assert period["missing_share_pct"] == 3.0

    def test_the_gap_closes_as_the_window_moves_forward(self):
        """Fewer companies remain to be delisted as time passes, so a recent
        backtest is less biased than an old one."""
        rows = [_row("A", "2020-06-01"), _row("B", "2023-06-01")]
        out = sv.bias_report({"2020-01": 100, "2022-01": 100}, rows)
        assert out["periods"][0]["missing"] == 2
        assert out["periods"][1]["missing"] == 1

    def test_the_worst_month_is_identified(self):
        rows = [_row("A", "2021-01-01"), _row("B", "2025-01-01")]
        out = sv.bias_report({"2020-01": 100, "2024-01": 100}, rows)
        assert out["worst_month"]["month"] == "2020-01"

    def test_it_says_plainly_that_it_does_not_fix_anything(self):
        out = sv.bias_report({"2020-01": 100}, [_row("A", "2021-01-01")])
        assert any("does not close it" in x for x in out["limitations"])

    def test_no_data_fails_closed(self):
        assert sv.bias_report({"2020-01": 100}, [])["error"] == "no_delisting_data"


class TestRealFile:
    def test_the_checked_in_list_parses(self):
        rows = sv.load_delistings()
        if not rows:
            return  # file absent in this checkout
        assert len(rows) > 400
        assert all(r["symbol"] and r["delisted_on"] for r in rows)

    def test_the_export_is_not_utf8(self):
        """Company names carry non-breaking spaces; reading it as UTF-8 raises."""
        assert sv.FILE_ENCODING == "latin-1"

    def test_most_delistings_were_not_voluntary(self):
        rows = sv.load_delistings()
        if not rows:
            return
        failures = sum(1 for r in rows if r["category"] == "failure")
        assert failures > len(rows) * 0.5, "forced exits should dominate"
