"""FIL — peer sync upgrades seed panels to live filing panels."""

from __future__ import annotations

from filing_intelligence.ingestion.store import reset_for_tests
from filing_intelligence.peer_sync import live_panel_for, overlay_peer_series
from peer_intelligence.peer_database.packs import pack_by_id
from peer_intelligence.peer_database.packs.banks_india import pack as raw_banks_pack


def setup_function() -> None:
    reset_for_tests()


def test_live_panel_hdfc():
    panel = live_panel_for("HDFCBANK")
    assert panel["live"] is True
    assert "CET1" in panel["series"]
    assert panel["series"]["CET1"]["data_class"] == "live_filing"


def test_overlay_marks_live_filing():
    raw = raw_banks_pack()
    synced = overlay_peer_series(raw)
    assert synced.get("filing_sync", {}).get("enabled") is True
    hdfc_casa = next(s for s in synced["series"] if s["entity"] == "HDFCBANK" and s["metric"] == "CASA")
    assert hdfc_casa["data_class"] == "live_filing"
    assert hdfc_casa["points"]["Q1FY27"] == 32.3


def test_pack_loader_soft_wires_fil():
    pack = pack_by_id("banks_india_v1")
    assert pack is not None
    assert pack.get("filing_sync", {}).get("refreshed")
