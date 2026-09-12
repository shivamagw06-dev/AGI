"""PIL — banking peer pack."""

from __future__ import annotations

from peer_intelligence.peer_database.packs.banks_india import pack
from peer_intelligence.production import analyse


def test_banks_pack_universe():
    p = pack()
    assert set(p["direct_universe"]) == {"HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN"}
    assert "JPM" in p["global_universe"]
    metrics = {s["metric"] for s in p["series"]}
    assert {"CASA", "NIM", "CET1", "ROE", "GNPA"} <= metrics


def test_hdfc_analyse_produces_scorecard():
    out = analyse("HDFCBANK")
    assert out["enabled"] is True
    assert out["scorecard"]["found"] is True
    assert out["commentary"]["trajectory_insight"]
