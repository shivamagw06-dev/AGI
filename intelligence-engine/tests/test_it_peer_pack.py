"""PIL — IT services peer pack."""

from __future__ import annotations

from peer_intelligence.peer_database.packs.it_services import pack
from peer_intelligence.rankings.engine import rankings_for


def test_it_pack_tcs_leads_ebit():
    p = pack()
    assert set(p["direct_universe"]) == {"TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"}
    ranks = rankings_for("TCS")
    ebit = next(r for r in ranks["metric_ranks"] if r["metric"] == "EBIT_Margin")
    assert ebit["rank"] == 1
