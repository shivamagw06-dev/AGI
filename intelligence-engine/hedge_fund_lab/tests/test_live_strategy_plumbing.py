"""The per-engine signal must actually reach the strategies.

First deploy of live_strategies returned 0 rows for all three strategies while
the engines were producing signal. fetch_live_alpha_rows aggregates per symbol
and previously discarded the per-engine map, exposing only
`contributing_engines` as human labels ("Breakout"). The strategies filtered on
sig["engine"], a key that did not exist on the returned rows, so the filter
could never match and every strategy was permanently empty.

That failure is indistinguishable from "the market is quiet" unless something
pins it, which is what these tests do.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import live_strategies as ls


@pytest.fixture(autouse=True)
def _clear_cache():
    """board() caches signals and vendor tables across strategies within a
    request. Without a reset the first test's fixture leaks into the rest."""
    ls.reset_cache()
    yield
    ls.reset_cache()


def _payload():
    """Shape returned by fetch_live_alpha_rows, including the per-engine map."""
    return {
        "ok": True,
        "rows": [
            {
                "ticker": "ALPHA", "symbol": "ALPHA", "sector": "IT",
                "direction": "positive", "contributing_engines": ["Breakout"],
                "engines": {
                    "opening_range_expansion_v1": {
                        "symbol": "ALPHA", "engine": "opening_range_expansion_v1",
                        "direction": "positive", "alpha_z": 2.4,
                        "signal_quality_score": 82, "price_at_signal": 500.0,
                        "factor_values": {},
                    },
                },
            },
            {
                "ticker": "BETA", "symbol": "BETA", "sector": "Materials",
                "direction": "negative", "contributing_engines": ["Dislocation", "Activity"],
                "engines": {
                    "intraday_mean_reversion_v1": {
                        "symbol": "BETA", "engine": "intraday_mean_reversion_v1",
                        "direction": "negative", "alpha_z": -1.8,
                        "signal_quality_score": 71, "price_at_signal": 250.0,
                        "factor_values": {},
                    },
                    "volume_liquidity_anomaly_v1": {
                        "symbol": "BETA", "engine": "volume_liquidity_anomaly_v1",
                        "direction": "negative", "alpha_z": -2.1,
                        "signal_quality_score": 65, "price_at_signal": 250.0,
                        "factor_values": {},
                    },
                },
            },
        ],
    }


def _patch(monkeypatch, payload=None):
    monkeypatch.setattr(ls, "fetch_live_alpha_rows", lambda **_: payload or _payload())
    monkeypatch.setattr(ls, "_risk_and_liquidity", lambda: (
        {"ALPHA": {"symbol": "ALPHA", "atr": 10.0, "beta_1y": 1.2, "sma50": 495.0},
         "BETA": {"symbol": "BETA", "atr": 6.0, "beta_1y": 0.8, "sma50": 248.0}},
        {"ALPHA": {"symbol": "ALPHA", "adv_3m": 4.0},
         "BETA": {"symbol": "BETA", "adv_3m": 1.5}},
    ))


class TestEngineRouting:
    def test_breakout_sees_only_its_own_engine(self, monkeypatch):
        _patch(monkeypatch)
        out = ls.scan_opening_range_breakout(limit=10)
        assert out["count"] == 1
        assert out["results"][0]["ticker"] == "ALPHA"

    def test_reversion_sees_only_its_own_engine(self, monkeypatch):
        _patch(monkeypatch)
        out = ls.scan_intraday_reversion(limit=10)
        assert [r["ticker"] for r in out["results"]] == ["BETA"]

    def test_flow_sees_only_its_own_engine(self, monkeypatch):
        _patch(monkeypatch)
        out = ls.scan_flow_anomaly(limit=10)
        assert [r["ticker"] for r in out["results"]] == ["BETA"]

    def test_a_symbol_on_two_engines_appears_in_both(self, monkeypatch):
        """BETA carries Dislocation and Activity; each strategy must see it."""
        _patch(monkeypatch)
        assert ls.scan_intraday_reversion(10)["count"] == 1
        assert ls.scan_flow_anomaly(10)["count"] == 1

    def test_rows_missing_the_engines_map_yield_nothing(self, monkeypatch):
        """Guards the original bug: no per-engine map means no rows, loudly."""
        _patch(monkeypatch, {"ok": True, "rows": [{"ticker": "X", "symbol": "X",
                                                   "contributing_engines": ["Breakout"]}]})
        assert ls.scan_opening_range_breakout(10)["count"] == 0


class TestRowContent:
    def test_carries_signal_and_sizing(self, monkeypatch):
        _patch(monkeypatch)
        row = ls.scan_opening_range_breakout(10)["results"][0]
        assert row["engine"] == "Breakout"
        assert row["signal_quality"] == 82
        assert row["price"] == 500.0 and row["price_source"] == "price_at_signal"
        assert row["sizing"]["target_weight"] is not None
        assert row["sizing"]["binding_constraint"] in {
            "volatility_target", "liquidity", "max_weight"}

    def test_missing_signal_price_is_never_replaced_by_sma50(self, monkeypatch):
        payload = _payload()
        signal = payload["rows"][0]["engines"]["opening_range_expansion_v1"]
        signal.pop("price_at_signal")
        signal["factor_values"] = {}
        _patch(monkeypatch, payload)
        row = ls.scan_opening_range_breakout(10)["results"][0]
        assert row["price"] is None
        assert row["price_source"] is None
        assert row["sizing"]["target_weight"] is None

    def test_breakout_places_an_atr_stop_below_for_a_long(self, monkeypatch):
        _patch(monkeypatch)
        row = ls.scan_opening_range_breakout(10)["results"][0]
        assert row["stop"] == 500.0 - ls.ATR_STOP_MULTIPLE * 10.0

    def test_reversion_exposes_the_hedge_ratio(self, monkeypatch):
        _patch(monkeypatch)
        row = ls.scan_intraday_reversion(10)["results"][0]
        assert row["market_hedge_ratio"] == 0.8

    def test_every_row_states_its_policy(self, monkeypatch):
        _patch(monkeypatch)
        for fn in (ls.scan_opening_range_breakout, ls.scan_intraday_reversion, ls.scan_flow_anomaly):
            for row in fn(10)["results"]:
                assert "no buy, sell" in row["policy"]
