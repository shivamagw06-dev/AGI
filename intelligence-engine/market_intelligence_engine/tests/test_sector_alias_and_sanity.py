"""Sector alias resolution + change-cap sanity for MSI."""

from __future__ import annotations

from market_intelligence_engine.service import _resolve_sector_name
from market_intelligence_engine.universe import _pct_change


def test_resolve_it_alias():
    available = ["Information Technology", "Financials", "Energy"]
    assert _resolve_sector_name("IT", available) == "Information Technology"
    assert _resolve_sector_name("it", available) == "Information Technology"
    assert _resolve_sector_name("Information Technology", available) == "Information Technology"


def test_pct_change_caps_and_rejects_tiny_base():
    assert _pct_change(20.0, 22.0) == 10.0
    # Tiny prior PE must not explode to millions of percent.
    assert _pct_change(0.0002, 32.0) is None
    capped = _pct_change(1.0, 100.0)
    assert capped is not None
    assert abs(capped) <= 150.0
