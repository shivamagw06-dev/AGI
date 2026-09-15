"""PIL — peer resolver."""

from __future__ import annotations

from peer_intelligence.resolver.resolve import resolve_peers


def test_hdfc_resolves_indian_and_global_peers():
    out = resolve_peers("HDFCBANK")
    assert out["resolved"] is True
    direct = {p["ticker"] for p in out["direct"]}
    assert {"ICICIBANK", "AXISBANK", "KOTAKBANK"} <= direct
    globals_ = {p["ticker"] for p in out["global_leaders"]}
    regionals = {p["ticker"] for p in out["regional_leaders"]}
    assert "JPM" in globals_
    assert "DBS" in regionals
    assert "SBIN" in out["direct_universe"] or any(p["ticker"] == "SBIN" for p in out["sector_leaders"])


def test_nestle_and_tcs_resolve():
    nestle = resolve_peers("NESTLEIND")
    assert nestle["resolved"]
    assert any(p["ticker"] == "HINDUNILVR" for p in nestle["direct"])
    tcs = resolve_peers("TCS")
    assert any(p["ticker"] == "INFY" for p in tcs["direct"])
    assert any(p["ticker"] == "ACN" for p in tcs["global_leaders"])


def test_unknown_ticker():
    out = resolve_peers("NOTAREALTICKER")
    assert out["resolved"] is False
