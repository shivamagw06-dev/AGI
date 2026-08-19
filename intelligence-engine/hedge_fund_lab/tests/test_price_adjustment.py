"""Corporate-action adjustment, checked against hand-computed values.

The warehouse's adjusted_close column is empty (0 of 500 sampled rows on
2026-08-19), so returns must be computed from an adjustment built here. Getting
it wrong is not a subtle error: a 1:1 bonus halves the quoted price with no
economic loss, and an unadjusted series records that as a -50% month.
"""

from __future__ import annotations

from datetime import date

import pytest

from hedge_fund_lab import price_adjustment as pa


class TestRatioParsing:
    @pytest.mark.parametrize("raw,expected", [
        ("1:2", 0.5), ("1 : 5", 0.2), ("1-10", 0.1), ("2:10", 0.2), ("10", 0.1),
    ])
    def test_split_factor(self, raw, expected):
        assert pa.split_factor(raw) == pytest.approx(expected)

    def test_bonus_one_for_one_halves_prior_prices(self):
        """1:1 bonus — one new share per share held, so 1 becomes 2."""
        assert pa.bonus_factor("1:1") == pytest.approx(0.5)

    def test_bonus_one_for_two(self):
        """1:2 — one new per two held, so 2 becomes 3."""
        assert pa.bonus_factor("1:2") == pytest.approx(2 / 3)

    def test_unparseable_returns_none(self):
        for bad in (None, "", "-", "0", "n/a", "abc"):
            assert pa.split_factor(bad) is None
            assert pa.bonus_factor(bad) is None


class TestActionClassification:
    def test_rights_are_refused_not_guessed(self):
        """A wrong rights adjustment shifts the whole prior history silently."""
        factor, reason = pa.action_factor({"action_type": "rights", "rights": "1:4"})
        assert factor is None
        assert reason == "rights_not_adjusted"

    def test_dividends_do_not_adjust_a_price_return_series(self):
        factor, reason = pa.action_factor({"action_type": "dividend", "dividend": 5.0})
        assert factor is None
        assert reason == "dividend_price_return_only"

    def test_split_is_applied(self):
        factor, reason = pa.action_factor({"action_type": "split", "split": "1:5"})
        assert factor == pytest.approx(0.2)
        assert reason is None


class TestSeriesAdjustment:
    def test_a_split_removes_the_artificial_drop(self):
        """The whole point: a 1:2 split must not read as a -50% month."""
        prices = [(date(2023, 1, 31), 1000.0), (date(2023, 2, 28), 500.0)]
        factors = [(date(2023, 2, 10), 0.5)]  # 1:2 split mid-period
        adjusted = pa.adjust_series(prices, factors)
        rets = pa.monthly_returns(adjusted)
        assert rets[0][1] == pytest.approx(0.0, abs=1e-9)

    def test_unadjusted_series_would_have_shown_minus_fifty(self):
        """Demonstrates the error being corrected."""
        raw = [(date(2023, 1, 31), 1000.0), (date(2023, 2, 28), 500.0)]
        assert pa.monthly_returns(raw)[0][1] == pytest.approx(-0.5)

    def test_most_recent_price_is_never_restated(self):
        prices = [(date(2023, 1, 31), 1000.0), (date(2023, 3, 31), 480.0)]
        factors = [(date(2023, 2, 10), 0.5)]
        adjusted = pa.adjust_series(prices, factors)
        assert adjusted[-1][1] == pytest.approx(480.0)

    def test_multiple_actions_compound(self):
        """A 1:2 split then a 1:1 bonus scales the earliest price by 0.25."""
        prices = [(date(2022, 1, 31), 1000.0), (date(2024, 1, 31), 250.0)]
        factors = [(date(2023, 6, 1), 0.5), (date(2022, 6, 1), 0.5)]
        adjusted = pa.adjust_series(prices, factors)
        assert adjusted[0][1] == pytest.approx(250.0)
        assert pa.monthly_returns(adjusted)[0][1] == pytest.approx(0.0, abs=1e-9)

    def test_actions_before_the_window_do_not_apply(self):
        prices = [(date(2024, 1, 31), 100.0), (date(2024, 2, 29), 110.0)]
        factors = [(date(2020, 1, 1), 0.5)]
        assert pa.monthly_returns(pa.adjust_series(prices, factors))[0][1] == pytest.approx(0.1)

    def test_empty_inputs_are_safe(self):
        assert pa.adjust_series([], [(date(2023, 1, 1), 0.5)]) == []
        assert pa.monthly_returns([]) == []


class TestFactorIndex:
    def test_groups_by_symbol_and_skips_unusable(self):
        actions = [
            {"symbol": "AAA", "action_date": "2023-01-10", "action_type": "split", "split": "1:2"},
            {"symbol": "AAA", "action_date": "2022-01-10", "action_type": "bonus", "bonus": "1:1"},
            {"symbol": "BBB", "action_date": "2023-01-10", "action_type": "rights", "rights": "1:4"},
            {"symbol": "CCC", "action_date": "2023-01-10", "action_type": "dividend", "dividend": 5},
        ]
        idx = pa.build_factors(actions)
        assert set(idx) == {"AAA"}, "rights and dividends must not create factors"
        assert len(idx["AAA"]) == 2
        assert idx["AAA"][0][0] > idx["AAA"][1][0], "newest first"


class TestAudit:
    def test_reports_what_it_could_not_handle(self):
        """An adjustment that silently drops the unparseable is as dangerous
        as no adjustment. This is the CORPORATE_ACTION_UNVERIFIED receipt."""
        actions = [
            {"symbol": "AAA", "action_date": "2023-01-10", "action_type": "split", "split": "1:2"},
            {"symbol": "BBB", "action_date": "2023-01-10", "action_type": "rights", "rights": "1:4"},
            {"symbol": "CCC", "action_date": "2023-01-10", "action_type": "split", "split": "garbage"},
        ]
        report = pa.audit(actions)
        assert report["adjustments_applied"] == 1
        assert report["breakdown"]["rights_not_adjusted"] == 1
        assert report["breakdown"]["unparseable_split"] == 1
        assert any("Rights" in x for x in report["limitations"])
