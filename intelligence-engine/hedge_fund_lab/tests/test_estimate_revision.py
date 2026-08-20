"""Estimate-revision signal construction, and the traps in it.

The dangerous one is the April fiscal roll. Comparing a fresh FY2027 estimate
against a stale FY2026 estimate produces a revision equal to the expected
growth rate, for every covered company at once, every April - a signal that
looks strong, is entirely artificial, and would rank the whole universe.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import estimate_revision as er


def _vintage(symbol, target, month, estimate, forward="true"):
    return {"symbol": symbol, "metric": "eps_estimate", "target_period": target,
            "consensus_date": f"{month}-28", "mean_estimate": estimate,
            "is_forward_estimate": forward}


def _bars(symbol, month, close, day="15"):
    return {"symbol": symbol, "date": f"{month}-{day}", "close": close}


class TestRevisionSignal:
    def test_measures_change_within_one_target_year(self):
        rows = [
            _vintage("AAA", "FY2026", "2025-04", 100.0),
            _vintage("AAA", "FY2026", "2025-07", 110.0),
        ]
        out = er.revision_scores(rows, lookback_months=3)
        assert out["2025-07"]["AAA"] == pytest.approx(0.10)

    def test_a_downgrade_reads_negative(self):
        rows = [
            _vintage("AAA", "FY2026", "2025-04", 100.0),
            _vintage("AAA", "FY2026", "2025-07", 80.0),
        ]
        assert er.revision_scores(rows, lookback_months=3)["2025-07"]["AAA"] == pytest.approx(-0.20)

    def test_the_fiscal_roll_does_not_create_a_signal(self):
        """April's FY2027 estimate must never be divided by March's FY2026 one.
        Unguarded, every covered company shows a large positive revision in the
        same month and the ranking becomes meaningless."""
        rows = [
            _vintage("AAA", "FY2026", "2026-01", 100.0),
            _vintage("AAA", "FY2027", "2026-04", 130.0),
        ]
        out = er.revision_scores(rows, lookback_months=3)
        assert out.get("2026-04", {}).get("AAA") is None

    def test_no_earlier_vintage_yields_no_signal(self):
        rows = [_vintage("AAA", "FY2026", "2025-07", 110.0)]
        assert er.revision_scores(rows, lookback_months=3) == {}

    def test_reported_actuals_are_ignored(self):
        rows = [
            _vintage("AAA", "FY2026", "2025-04", 100.0, forward="false"),
            _vintage("AAA", "FY2026", "2025-07", 110.0, forward="false"),
        ]
        assert er.revision_scores(rows, lookback_months=3) == {}

    def test_a_sign_flip_is_excluded_not_scaled(self):
        """Loss to profit is a change of kind, not a percentage revision."""
        rows = [
            _vintage("AAA", "FY2026", "2025-04", -5.0),
            _vintage("AAA", "FY2026", "2025-07", 5.0),
        ]
        assert er.revision_scores(rows, lookback_months=3) == {}

    def test_a_tiny_denominator_is_excluded(self):
        """An estimate of 0.01 turns any change into a four-figure revision."""
        rows = [
            _vintage("AAA", "FY2026", "2025-04", 0.02),
            _vintage("AAA", "FY2026", "2025-07", 2.0),
        ]
        assert er.revision_scores(rows, lookback_months=3) == {}

    def test_two_target_years_in_one_month_keep_the_larger_move(self):
        rows = [
            _vintage("AAA", "FY2026", "2025-04", 100.0),
            _vintage("AAA", "FY2026", "2025-07", 105.0),
            _vintage("AAA", "FY2027", "2025-04", 100.0),
            _vintage("AAA", "FY2027", "2025-07", 130.0),
        ]
        assert er.revision_scores(rows, lookback_months=3)["2025-07"]["AAA"] == pytest.approx(0.30)


class TestMonthlyPrices:
    def test_takes_the_last_trading_day_of_the_month(self):
        rows = [_bars("AAA", "2025-07", 100.0, "01"), _bars("AAA", "2025-07", 120.0, "31")]
        assert er.monthly_prices(rows)["AAA"]["2025-07"] == 120.0

    def test_weekend_bars_cannot_set_the_month_end_price(self):
        """Weekend rows carry a differently scaled series."""
        rows = [_bars("AAA", "2026-06", 375.0, "19"), _bars("AAA", "2026-06", 37.0, "21")]
        assert er.monthly_prices(rows)["AAA"]["2026-06"] == 375.0


class TestBacktest:
    def _universe(self, n=12):
        vintages, prices = [], []
        for i in range(n):
            sym = f"S{i:02d}"
            # Higher-numbered symbols get bigger upgrades and bigger returns, so
            # a working harness must find a positive result.
            vintages.append(_vintage(sym, "FY2026", "2025-04", 100.0))
            vintages.append(_vintage(sym, "FY2026", "2025-07", 100.0 + i))
            prices.append(_bars(sym, "2025-07", 100.0, "31"))
            prices.append(_bars(sym, "2025-08", 100.0 + i * 0.5, "29"))
        return vintages, prices

    def test_ranks_on_revision_and_measures_the_next_month(self):
        vintages, prices = self._universe()
        out = er.backtest(vintage_rows=vintages, price_rows=prices, holdings=5)
        assert out["ok"] is True
        period = next(p for p in out["periods"] if p["month"] == "2025-07")
        assert period["n"] == 5
        # Top five revisions are S07..S11, averaging +4.5% before costs.
        assert period["gross"] == pytest.approx(0.045, abs=1e-6)

    def test_costs_are_charged_on_turnover(self):
        vintages, prices = self._universe()
        out = er.backtest(vintage_rows=vintages, price_rows=prices, holdings=5, cost_bps=50)
        period = next(p for p in out["periods"] if p["month"] == "2025-07")
        assert period["net"] < period["gross"]
        assert period["turnover"] == pytest.approx(1.0)

    def test_annualises_by_twelve_not_by_sessions(self):
        """These are monthly returns. Annualising by 252 overstates by sqrt(21)."""
        # The metric rounds to three decimals, so compare at that precision.
        assert er._metrics([0.01] * 12)["annualised_return_pct"] == pytest.approx(
            ((1.01 ** 12) - 1) * 100, abs=1e-3)
        # A 252-session annualisation would report roughly 1,180% instead.
        assert er._metrics([0.01] * 12)["annualised_return_pct"] < 20

    def test_a_thin_month_produces_no_portfolio(self):
        vintages = [_vintage("AAA", "FY2026", "2025-04", 100.0),
                    _vintage("AAA", "FY2026", "2025-07", 110.0)]
        prices = [_bars("AAA", "2025-07", 100.0), _bars("AAA", "2025-08", 110.0)]
        out = er.backtest(vintage_rows=vintages, price_rows=prices)
        period = next(p for p in out["periods"] if p["month"] == "2025-07")
        assert period["net"] is None
        assert period["reason"] == "too_few_priced_candidates"

    def test_fails_closed_without_a_signal(self):
        assert er.backtest(vintage_rows=[], price_rows=[])["error"] == "no_revision_signal"

    def test_survivorship_is_stated_on_every_result(self):
        vintages, prices = self._universe()
        out = er.backtest(vintage_rows=vintages, price_rows=prices, holdings=5)
        assert any("SURVIVORSHIP" in line for line in out["limitations"])
        assert "alpha claim" in out["verdict"]
