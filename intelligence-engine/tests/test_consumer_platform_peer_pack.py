"""PIL — consumer internet peer pack."""

from __future__ import annotations

from peer_intelligence.peer_database.packs.consumer_internet import pack
from peer_intelligence.resolver.resolve import resolve_peers


def test_eternal_resolves_marketplace_peers():
    p = pack()
    assert "ETERNAL" in p["direct_universe"]
    assert "UBER" in p["global_universe"]
    out = resolve_peers("ZOMATO")  # alias
    assert out["resolved"] is True
    assert out["ticker"] == "ETERNAL"
