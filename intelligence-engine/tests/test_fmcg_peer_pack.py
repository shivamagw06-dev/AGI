"""PIL — FMCG peer pack."""

from __future__ import annotations

from peer_intelligence.peer_database.packs.fmcg_india import pack
from peer_intelligence.percentile.engine import percentiles_for


def test_fmcg_pack_and_nestle_roic_rank():
    p = pack()
    assert "NESTLEIND" in p["direct_universe"]
    assert "NESN" in p["global_universe"]
    pct = percentiles_for("NESTLEIND")
    roic = next(x for x in pct["percentiles"] if x["metric"] == "ROIC")
    assert roic["rank"] == 1
