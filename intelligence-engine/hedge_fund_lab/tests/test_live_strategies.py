"""Sizing arithmetic for the intraday-native strategies.

These pin the formulas the desk prints beside the table, so the page and the
engine cannot drift apart silently. Every constant is deliberately checked
against a hand-computed value rather than a snapshot of the implementation.
"""

from __future__ import annotations

import math

import pytest

from hedge_fund_lab import live_strategies as ls


class TestAnnualisedVol:
    def test_matches_hand_calculation(self):
        # ATR 20 on a price of 1000 is 2% daily; annualised = 0.02 * sqrt(252)
        got = ls.annualised_vol(20.0, 1000.0)
        assert got == pytest.approx(0.02 * math.sqrt(252), rel=1e-9)

    def test_missing_inputs_return_none(self):
        assert ls.annualised_vol(None, 1000.0) is None
        assert ls.annualised_vol(20.0, None) is None
        assert ls.annualised_vol(20.0, 0.0) is None


class TestVolTargetWeight:
    def test_matches_hand_calculation(self):
        # w = sigma_target / (sigma * sqrt(N))
        got = ls.vol_target_weight(0.30, n=25)
        assert got == pytest.approx(ls.VOL_TARGET / (0.30 * 5.0), rel=1e-9)

    def test_higher_volatility_gets_less_weight(self):
        assert ls.vol_target_weight(0.20) > ls.vol_target_weight(0.60)

    def test_degenerate_inputs(self):
        assert ls.vol_target_weight(0.0) is None
        assert ls.vol_target_weight(0.2, n=0) is None


class TestAdvCap:
    def test_converts_millions_of_shares_to_value(self):
        # Capital IQ reports ADV in millions of shares. 10mn shares at Rs 500
        # is Rs 5,000,000,000 of daily value; 10% of that over Rs 1bn capital.
        got = ls.adv_cap(10.0, 500.0, capital=1_000_000_000)
        assert got == pytest.approx((0.10 * 10.0 * 1e6 * 500.0) / 1_000_000_000, rel=1e-9)

    def test_illiquid_name_is_capped_hard(self):
        thin = ls.adv_cap(0.01, 50.0, capital=1_000_000_000)
        deep = ls.adv_cap(20.0, 2000.0, capital=1_000_000_000)
        assert thin < deep
        assert thin < 0.001

    def test_missing_inputs_return_none(self):
        assert ls.adv_cap(None, 100.0) is None
        assert ls.adv_cap(5.0, None) is None


class TestSizePosition:
    def test_takes_the_minimum_of_all_limits(self):
        out = ls.size_position(price=1000.0, atr=20.0, adv_shares_mn=50.0)
        limits = [out["vol_target_weight"], out["liquidity_cap_weight"], out["max_weight"]]
        assert out["target_weight"] == pytest.approx(min(limits), rel=1e-9)

    def test_illiquidity_binds_for_a_thin_name(self):
        out = ls.size_position(price=50.0, atr=1.0, adv_shares_mn=0.005)
        assert out["binding_constraint"] == "liquidity"

    def test_max_weight_binds_for_a_calm_liquid_name(self):
        out = ls.size_position(price=1000.0, atr=1.0, adv_shares_mn=500.0)
        assert out["binding_constraint"] == "max_weight"
        assert out["target_weight"] == ls.MAX_WEIGHT

    def test_unsizeable_without_atr(self):
        out = ls.size_position(price=1000.0, atr=None, adv_shares_mn=50.0)
        assert out["vol_target_weight"] is None
        assert out["target_weight"] is not None  # liquidity + max still bound

    def test_notional_follows_the_weight(self):
        out = ls.size_position(price=1000.0, atr=20.0, adv_shares_mn=50.0)
        assert out["notional_inr"] == round(out["target_weight"] * ls.PORTFOLIO_CAPITAL)


class TestCoverage:
    def test_reports_what_is_missing_rather_than_defaulting(self):
        cov = ls._coverage({"atr": 5.0}, None)
        assert cov["complete"] is False
        assert "adv" in cov["missing"] and "beta" in cov["missing"]
        assert cov["sizeable"] is False

    def test_complete_when_all_present(self):
        cov = ls._coverage({"atr": 5.0, "beta_1y": 1.1}, {"adv_3m": 3.0})
        assert cov["complete"] is True and cov["sizeable"] is True

    def test_sizeable_without_beta(self):
        """Beta is needed to hedge, not to size — the two must not be conflated."""
        cov = ls._coverage({"atr": 5.0}, {"adv_3m": 3.0})
        assert cov["sizeable"] is True
        assert "beta" in cov["missing"]


class TestBoardContract:
    def test_declares_its_own_validation_state(self):
        board = ls.board(limit=1)
        v = board["validation"]
        assert v["alpha_claims_permitted"] is False
        assert v["backtest"] == "NOT RUN"
        assert "FAILING" in v["point_in_time"]
        assert "FAILING" in v["survivorship"]

    def test_exposes_every_sizing_constant(self):
        c = ls.board(limit=1)["sizing_constants"]
        for key in ("vol_target", "max_weight", "adv_participation",
                    "portfolio_capital_inr", "holdings", "atr_stop_multiple"):
            assert key in c

    def test_one_card_per_strategy_even_on_failure(self):
        board = ls.board(limit=1)
        assert len(board["cards"]) == len(ls.LIVE_STRATEGIES)
        assert {c["strategy"] for c in board["cards"]} == set(ls.LIVE_STRATEGIES)
