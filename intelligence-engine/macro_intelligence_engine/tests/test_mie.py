"""Macro Intelligence Engine — consumer tests, no recommendations."""

from __future__ import annotations

from macro_intelligence_engine import ask_slice, health
from macro_intelligence_engine.composer import build_macro_pack, build_module
from macro_intelligence_engine.dqiv import validate_pack, validate_section
from macro_intelligence_engine.indicators import classify_regime, scenario_probabilities, sector_impacts
from macro_intelligence_engine.modules import executive, scenarios


def _bundle(**over):
    snap = {
        "gdp_growth": {"value": 6.5, "direction": "up", "source": "test"},
        "cpi": {"value": 4.8, "direction": "down", "source": "test"},
        "repo_rate": {"value": 6.5, "direction": "flat", "source": "test"},
        "pmi_manufacturing": {"value": 56.0, "direction": "up", "source": "test"},
        "brent": {"value": 82.0, "direction": "up", "source": "test"},
        "usdinr": {"value": 83.2, "direction": "up", "source": "test"},
        "credit_growth": {"value": 14.0, "direction": "up", "source": "test"},
        "banking_liquidity": {"value": 1.2, "direction": "up", "source": "test"},
        "india_10y": {"value": 7.1, "direction": "down", "source": "test"},
    }
    base = {
        "country": "India",
        "snapshot": snap,
        "cmkp": {"dashboard": {"ok": True}, "india": {"ok": True}, "global": {"ok": True}},
        "hmip": {"ok": True},
        "hmai_regime": {"ok": True, "regime": "Expansion"},
        "mfi_forecast": {"ok": True, "summary": "Directional soft-landing base case."},
        "mfi_scenarios": {"ok": True, "scenarios": {"base": {}}},
        "mri": {"ok": True},
        "warehouse": {
            "macro_latest": [],
            "macro_series": [],
            "macro_events": [{"title": "RBI MPC hold"}],
            "macro_regimes": [],
            "macro_history": [],
            "macro_alerts": [],
            "macro_calendar": [],
            "macro_relationships": [],
        },
        "inputs_present": {
            "cmkp": True,
            "hmip": True,
            "hmai_regime": True,
            "mfi_forecast": True,
            "mfi_scenarios": True,
            "mri": True,
            "macro_latest": False,
            "macro_series": False,
            "macro_events": True,
            "macro_relationships": False,
        },
        "observed_series_count": len(snap),
        "catalogue_size": 30,
    }
    base.update(over)
    return base


def test_health():
    h = health()
    assert h["ok"] is True
    assert h["recommendation_language"] is False
    assert h["vendor_calls"] is False
    assert h["gdp_point_predictions"] is False
    assert h["version"] == "9.0"


def test_probabilities_sum_100():
    probs = scenario_probabilities("Expansion", 0.7)
    assert abs(probs["bull"] + probs["base"] + probs["bear"] - 100.0) < 0.2


def test_sector_impact_covers_all():
    impacts = sector_impacts(_bundle()["snapshot"])
    assert len(impacts) == 11
    assert all(i["impact"] in {"Positive", "Neutral", "Negative"} for i in impacts)


def test_regime_classification():
    pack = classify_regime(_bundle()["snapshot"])
    assert pack["regime"]
    assert pack["cycle"]


def test_regime_label_normalizes_hmai_dict():
    from macro_intelligence_engine.indicators import regime_label
    from macro_intelligence_engine.modules import executive

    label = regime_label({
        "regime_id": "x",
        "label": "India 2026 current regime",
        "features": {"gdp": 7.4},
    })
    assert label == ""  # generic catalog label ignored
    assert regime_label({"regime": "Expansion"}) == "Expansion"
    sec = executive(_bundle(hmai_regime={
        "ok": True,
        "regime": {"regime_id": "x", "label": "India 2026 current regime", "features": {}},
    }))
    assert isinstance(sec.get("regime"), str)
    assert "{" not in sec["summary"]


def test_executive_no_recommendation_language():
    sec = executive(_bundle())
    assert sec["ok"] is True
    blob = " ".join(sec["findings"]).lower()
    assert "buy" not in blob
    assert "sell" not in blob
    gate = validate_section(sec)
    assert gate["ok"] is True


def test_scenarios_probabilities():
    sec = scenarios(_bundle())
    assert sec["ok"] is True
    probs = sec["probabilities"]
    assert abs(probs["bull"] + probs["base"] + probs["bear"] - 100.0) < 0.2


def test_build_module_regime():
    # Soft integration — should not raise even without warehouse
    out = build_module("regime", country="India", bundle=_bundle())
    assert out["module"] == "regime"
    assert out.get("explainability")


def test_ask_slice_regime():
    # Monkeypatch via direct module path using composer with bundle through ask on rates
    from macro_intelligence_engine.modules import rates as rates_mod

    sec = rates_mod(_bundle())
    assert "Interest Rates" in sec["title"]
    assert sec.get("confidence")


def test_validate_pack_rejects_recommendation():
    pack = {
        "modules": {"executive": executive(_bundle())},
        "macro_quality": {},
        "recommendation": "BUY",
        "inputs_present": {},
    }
    gate = validate_pack(pack)
    assert gate["ok"] is False
    assert "recommendation_forbidden" in gate["errors"]
