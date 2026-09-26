"""Request-scoped Yahoo symbol / enrich cache."""

from __future__ import annotations

from app.market_data.providers.yahoo_request_cache import (
    begin_request_scope,
    cached_get,
    cached_set,
    end_request_scope,
)
from app.market_data.providers.yahoo_symbols import to_yahoo_symbol


def test_request_scope_memoises_symbol_resolution():
    token = begin_request_scope()
    try:
        a = to_yahoo_symbol("META")
        b = to_yahoo_symbol("META")
        assert a == "META"
        assert b == "META"
        assert cached_get("ysym:META|NSE") == "META"
        cached_set("yahoo_enrich:META", {"enabled": True, "symbol": "META"})
        assert cached_get("yahoo_enrich:META")["symbol"] == "META"
    finally:
        end_request_scope(token)
