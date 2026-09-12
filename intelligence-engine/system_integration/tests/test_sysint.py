"""System integration inventory tests."""

from __future__ import annotations

from system_integration.production import bootstrap, health, inventory


def test_inventory_lists_core_programmes() -> None:
    inv = inventory()
    assert inv["n"] >= 8
    shorts = {p["short"] for p in inv["programmes"]}
    for required in ("CMKTP", "MKFI", "SFI", "MFI", "RIH", "IIEX"):
        assert required in shorts
    assert inv["primary_knowledge_object"] == "ResearchObject"
    assert inv["providers_queried"] == []


def test_health_research_centric() -> None:
    h = health()
    assert h["research_centric"] is True
    assert h["ask_triggers_collection"] is False
    assert h["apis"]["rih"] == "/v1/research/hub"
    assert h["apis"]["mkfi"] == "/v1/market/forecast"


def test_bootstrap_rih_catalog() -> None:
    out = bootstrap(publish_rih=True, publish_mkfi=False)
    assert out["ask_triggered"] is False
    assert out["providers_queried"] == []
    assert any(a.get("programme") == "RIH" for a in out["actions"])
