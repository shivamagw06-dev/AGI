"""Corporate-action adjustment, pinned to gaps measured in production prices.

Every ratio assertion here is anchored to a real event verified on 2026-08-19
rather than to a convention assumed from documentation. The first version of
this module assumed `a:b` meant "a becomes b" and had the split factor
inverted; the price series says otherwise.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from hedge_fund_lab import price_adjustment as pa


def _weekdays(start: date, count: int, price: float) -> list[tuple[date, float]]:
    out, day = [], start
    while len(out) < count:
        if pa.is_trading_day(day):
            out.append((day, price))
        day += timedelta(days=1)
    return out


class TestSplitConvention:
    @pytest.mark.parametrize("raw,expected,event", [
        ("6:1", 1 / 6, "ZFCVINDIA 16086 -> 2660"),
        ("10:1", 0.1, "MWL 370.25 -> 36.65"),
        ("5:2", 0.4, "POCL 1401.8 -> 561.1"),
        ("2:1", 0.5, "LICI 2.06x gap"),
    ])
    def test_prior_prices_scale_by_b_over_a(self, raw, expected, event):
        assert pa.split_factor(raw) == pytest.approx(expected), event

    def test_the_inverted_reading_is_offered_separately(self):
        """A minority of rows - every 2:10 seen - are written the other way."""
        assert pa.split_factor_inverted("2:10") == pytest.approx(0.2)
        assert pa.split_factor("2:10") == pytest.approx(5.0)

    def test_unparseable_returns_none(self):
        for bad in (None, "", "-", "0", "n/a", "abc"):
            assert pa.split_factor(bad) is None
            assert pa.bonus_factor(bad) is None


class TestBonusConvention:
    def test_one_for_one_halves_prior_prices(self):
        """LICI's 1:1 bonus moved the price by 2.06x."""
        assert pa.bonus_factor("1:1") == pytest.approx(0.5)

    def test_one_for_two(self):
        """TRENT's 1:2 bonus moved the price by 1.52x, i.e. 2/3."""
        assert pa.bonus_factor("1:2") == pytest.approx(2 / 3)


class TestNonTradingDays:
    def test_weekends_are_not_trading_days(self):
        assert pa.is_trading_day(date(2026, 6, 19)) is True    # Friday
        assert pa.is_trading_day(date(2026, 6, 21)) is False   # Sunday

    def test_weekend_rows_are_dropped_from_the_series(self):
        """MWL printed a tenth of its weekday price every Sunday for months.
        Kept in, each weekend fabricates a -90% day and a +900% day."""
        prices = [
            (date(2026, 6, 19), 375.85),   # Friday
            (date(2026, 6, 21), 37.10),    # Sunday - corrupt
            (date(2026, 6, 22), 376.25),   # Monday
        ]
        out = pa.adjust_series(prices, [])
        assert [d for d, _ in out] == [date(2026, 6, 19), date(2026, 6, 22)]
        assert all(abs(r) < 0.05 for _, r in pa.monthly_returns(out))


class TestObservedGap:
    def test_measures_the_split_gap(self):
        pre = _weekdays(date(2026, 6, 1), 5, 1000.0)
        post = _weekdays(date(2026, 6, 22), 5, 250.0)
        gap = pa.observed_factor(pre + post, date(2026, 6, 22))
        assert gap == pytest.approx(0.25)

    def test_returns_none_without_enough_history(self):
        assert pa.observed_factor([(date(2026, 6, 1), 100.0)], date(2026, 6, 2)) is None


class TestReconciliation:
    def test_accepts_a_stated_ratio_the_prices_agree_with(self):
        factor, status = pa.reconcile([0.25, 4.0], observed=0.253)
        assert factor == 0.25 and status == "corroborated"

    def test_picks_whichever_reading_the_prices_support(self):
        """2:10 is written the other way round; only the gap can say so."""
        factor, _ = pa.reconcile([5.0, 0.2], observed=0.198)
        assert factor == pytest.approx(0.2)

    def test_refuses_when_the_prices_contradict_the_ratio(self):
        """DELPHIFX states 3:1 and the price gap is 16.4x. Guessing here would
        silently rescale the entire prior history."""
        factor, status = pa.reconcile([1 / 3, 3.0], observed=0.0608)
        assert factor is None
        assert status == "stated_ratio_contradicted_by_prices"

    def test_refuses_without_price_evidence(self):
        assert pa.reconcile([0.5], observed=None) == (None, "no_price_evidence")


class TestResolve:
    def test_duplicate_representations_of_one_event_collapse(self):
        """TRENT records one event as both a 1:2 bonus and a 3:2 split. Applying
        both would adjust by 0.44 instead of 0.67."""
        prices = _weekdays(date(2026, 5, 1), 6, 300.0) + _weekdays(date(2026, 6, 1), 6, 200.0)
        actions = [
            {"symbol": "TRENT", "action_date": "2026-06-01", "action_type": "bonus", "bonus": "1:2"},
            {"symbol": "TRENT", "action_date": "2026-06-01", "action_type": "split", "split": "3:2"},
        ]
        resolved = pa.resolve(prices, actions)
        assert len(resolved["factors"]) == 1
        assert resolved["factors"][0][1] == pytest.approx(2 / 3, rel=1e-3)

    def test_rights_and_dividends_create_no_factor(self):
        prices = _weekdays(date(2026, 5, 1), 12, 100.0)
        for kind, field in (("rights", "1:4"), ("dividend", 5)):
            resolved = pa.resolve(prices, [{"symbol": "X", "action_date": "2026-05-20",
                                            "action_type": kind, kind: field}])
            assert resolved["factors"] == []


class TestSeriesAdjustment:
    def test_a_split_removes_the_artificial_drop(self):
        prices = _weekdays(date(2026, 5, 1), 5, 1000.0) + _weekdays(date(2026, 6, 1), 5, 500.0)
        adjusted = pa.adjust_series(prices, [(date(2026, 6, 1), 0.5)])
        assert all(abs(r) < 1e-9 for _, r in pa.monthly_returns(adjusted))

    def test_most_recent_price_is_never_restated(self):
        prices = _weekdays(date(2026, 5, 1), 4, 1000.0) + _weekdays(date(2026, 6, 1), 4, 480.0)
        adjusted = pa.adjust_series(prices, [(date(2026, 6, 1), 0.5)])
        assert adjusted[-1][1] == pytest.approx(480.0)

    def test_actions_before_the_window_do_not_apply(self):
        prices = _weekdays(date(2026, 5, 1), 4, 100.0)
        adjusted = pa.adjust_series(prices, [(date(2020, 1, 1), 0.5)])
        assert adjusted[0][1] == pytest.approx(100.0)

    def test_empty_inputs_are_safe(self):
        assert pa.adjust_series([], [(date(2026, 1, 1), 0.5)]) == []
        assert pa.monthly_returns([]) == []


class TestBuildFactors:
    def test_nothing_is_applied_without_prices_to_check_against(self):
        """The previous version trusted the ratio string outright."""
        actions = [{"symbol": "AAA", "action_date": "2026-06-01",
                    "action_type": "split", "split": "1:2"}]
        assert pa.build_factors(actions) == {}

    def test_applies_only_the_corroborated_symbol(self):
        prices = {
            "GOOD": _weekdays(date(2026, 5, 1), 6, 1000.0) + _weekdays(date(2026, 6, 1), 6, 250.0),
            "BAD": _weekdays(date(2026, 5, 1), 6, 1000.0) + _weekdays(date(2026, 6, 1), 6, 990.0),
        }
        actions = [
            {"symbol": "GOOD", "action_date": "2026-06-01", "action_type": "split", "split": "4:1"},
            {"symbol": "BAD", "action_date": "2026-06-01", "action_type": "split", "split": "4:1"},
        ]
        out = pa.build_factors(actions, prices)
        assert set(out) == {"GOOD"}
        assert out["GOOD"][0][1] == pytest.approx(0.25)


class TestAudit:
    def test_declares_itself_unverifiable_without_prices(self):
        report = pa.audit([{"symbol": "A", "action_date": "2026-06-01",
                            "action_type": "split", "split": "1:2"}])
        assert report["corroborated_against_prices"] is False
        assert report["status"] == "UNVERIFIABLE_WITHOUT_PRICES"
        assert report["adjustments_applied"] == 0

    def test_reports_quarantined_symbols(self):
        prices = {"BAD": _weekdays(date(2026, 5, 1), 6, 1000.0)
                         + _weekdays(date(2026, 6, 1), 6, 990.0)}
        report = pa.audit([{"symbol": "BAD", "action_date": "2026-06-01",
                            "action_type": "split", "split": "4:1"}], prices)
        assert report["symbols_quarantined"] == 1
        assert report["breakdown"]["stated_ratio_contradicted_by_prices"] == 1
