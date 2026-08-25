"""Live LTP overlay for Hedge Fund scanners."""

from __future__ import annotations

from hedge_fund_lab.live_prices import apply_latest_live_price, lookup_live_price, reset_cache


def setup_function():
    reset_cache()


def test_prefers_instrument_key_then_ticker():
    latest = {
        "NSE_EQ|INE002A01018": {"ltp": 1300.6, "observed_at": "2026-08-25T07:00:00+00:00", "source": "live_market_snapshots"},
        "RELIANCE": {"ltp": 1300.6, "observed_at": "2026-08-25T07:00:00+00:00", "source": "live_market_snapshots"},
    }
    pack = lookup_live_price({"ticker": "RELIANCE", "instrument_key": "NSE_EQ|INE002A01018"}, latest)
    assert pack["ltp"] == 1300.6
    assert lookup_live_price({"ticker": "RELIANCE"}, latest)["ltp"] == 1300.6
    assert lookup_live_price({"ticker": "UNKNOWN"}, latest) is None


def test_overlays_price_and_recomputes_consensus_upside():
    row = apply_latest_live_price(
        {
            "ticker": "RELIANCE",
            "price": 1309.8,
            "consensus": {"target_price": 1600.0, "upside": 22.16},
            "data_context": {"valuation_source": "upstox"},
        },
        {"RELIANCE": {"ltp": 1300.6, "observed_at": "2026-08-25T07:00:00+00:00", "source": "live_market_snapshots"}},
    )
    assert row["price"] == 1300.6
    assert row["price_source"] == "live_market_snapshots"
    assert row["consensus"]["upside"] == round((1600.0 / 1300.6 - 1) * 100, 2)
    assert row["data_context"]["price_freshness"] == "LIVE"
    assert row["data_context"]["valuation_source"] == "upstox"
    assert row["live_price"] == 1300.6


def test_scales_dividend_yield_with_the_new_print():
    row = apply_latest_live_price(
        {"ticker": "ITC", "price": 400.0, "dividend_yield": 4.0},
        {"ITC": {"ltp": 500.0, "observed_at": "2026-08-25T07:00:00+00:00", "source": "live_market_snapshots"}},
    )
    assert row["dividend_yield"] == 3.2


def test_recomputes_forward_pe_from_forward_eps_and_leaves_trailing_pe():
    row = apply_latest_live_price(
        {"ticker": "ITC", "price": 400.0, "pe": 24.5, "forward_eps": 25.0},
        {"ITC": {"ltp": 500.0, "observed_at": "2026-08-25T07:00:00+00:00", "source": "live_market_snapshots"}},
    )
    assert row["forward_pe"] == 20.0
    assert row["pe"] == 24.5


def test_leaves_the_row_alone_when_no_live_print():
    row = {"ticker": "AUTOIND", "price": 96.15}
    assert apply_latest_live_price(row, {}) is row


def test_walks_a_terminal_payload():
    from hedge_fund_lab.live_prices import overlay_live_prices_on_payload

    payload = overlay_live_prices_on_payload(
        {
            "cards": [{
                "results": [{
                    "ticker": "RELIANCE",
                    "price": 1309.8,
                    "market": {"price": 1309.8},
                    "consensus": {"target_price": 1600.0, "upside": 22.16},
                }],
            }],
        },
        {"RELIANCE": {"ltp": 1300.6, "observed_at": "2026-08-25T07:00:00+00:00", "source": "live_market_snapshots"}},
    )
    row = payload["cards"][0]["results"][0]
    assert row["price"] == 1300.6
    assert row["market"]["price"] == 1300.6
    assert row["data_context"]["price_freshness"] == "LIVE"
