"""NSE EQUITY_L trading universe — all cash equities available for trading."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_nifty_stocks_and_equity_l_present():
    assert (REPO / "NIFTYstocks.csv").exists()
    assert (REPO / "EQUITY_L.csv").exists()


def test_trading_universe_health_and_count():
    from trading_universe.loader import health, list_symbols, _cached_rows

    _cached_rows.cache_clear()
    h = health()
    assert h["ok"] is True
    assert h["count"] >= 2300
    assert h["role"] == "all_equity_stocks_available_for_trading"
    symbols = list_symbols()
    assert "IDBI" in symbols
    assert "HDFCBANK" in symbols
    assert "RELIANCE" in symbols


def test_trading_universe_search_idbi():
    from trading_universe.loader import get_symbol, search

    hits = search("idbi bank", limit=5)
    assert hits
    assert any(h["symbol"] == "IDBI" for h in hits)
    row = get_symbol("IDBI")
    assert row and row["tradable"] is True


def test_production_hardening_all_preset():
    from production_hardening.universe import resolve_universe

    uni = resolve_universe(preset="all")
    assert uni["n"] >= 2300
    assert uni["source"] == "nse_trading_universe"
    assert "IDBI" in uni["symbols"]


def test_supported_universe_includes_nse_listed():
    from knowledge_factory.historical_depth.universe_priority import (
        nse_listed,
        priority_tier,
        supported_universe,
    )

    nse = nse_listed()
    assert len(nse) >= 2300
    assert "IDBI" in supported_universe()
    # IDBI is a Nifty 500 constituent (tier 5 in the index-CSV-based priority
    # scheme: 1=Nifty50 2=Next50 3=Nifty100 4=Nifty200 5=Nifty500 ... 7=residual NSE).
    assert priority_tier("IDBI") <= 7
