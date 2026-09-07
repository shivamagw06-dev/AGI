"""Research Intelligence Engine — dossier consumer, no recommendations."""

from __future__ import annotations

from research_intelligence_engine import ask_slice, health
from research_intelligence_engine.composer import build_dossier, build_section
from research_intelligence_engine.dqiv import validate_dossier, validate_section
from research_intelligence_engine.sections import executive, risk, valuation


def _bundle(**over):
    base = {
        "symbol": "INFY",
        "master": {"symbol": "INFY", "company_name": "Infosys", "sector": "IT", "industry": "IT Services"},
        "annual": [
            {"fiscal_year": "FY24", "revenue": 150000, "pat": 25000, "roe": 28, "equity": 80000, "total_debt": 2000,
             "operating_cash_flow": 24000},
            {"fiscal_year": "FY25", "revenue": 165000, "pat": 27000, "roe": 30, "equity": 90000, "total_debt": 1500,
             "operating_cash_flow": 26000},
        ],
        "quarterly": [],
        "ownership": [{"promoter_pct": 14.5, "fii_pct": 33.0, "dii_pct": 22.0, "as_of": "2026-03-31"}],
        "corporate_actions": [{"date": "2025-06-01", "action_type": "dividend"}],
        "valuation_ratios": [{"roe": 30, "roce": 35, "operating_margin": 22}],
        "historical_valuation": [{"date": "2026-01-01", "pe": 24}],
        "historical_statistics": [],
        "research_timeline": [{"date": "2026-01-15", "event": "valuation_regime_changed"}],
        "research_documents": [{"summary": "Services and digital offerings.", "strategy": "Large deal focus", "risks": "Wage inflation"}],
        "latest_annual": {
            "fiscal_year": "FY25", "revenue": 165000, "pat": 27000, "roe": 30, "equity": 90000,
            "total_debt": 1500, "operating_cash_flow": 26000,
        },
        "prev_annual": {"fiscal_year": "FY24", "revenue": 150000, "pat": 25000, "roe": 28},
        "latest_ratio": {"roe": 30, "roce": 35, "operating_margin": 22},
        "latest_ownership": {"promoter_pct": 14.5, "fii_pct": 33.0, "dii_pct": 22.0},
        "uve": {"ok": True, "primary_model": "PE"},
        "vpae": {"ok": True, "primary_model": "PE", "primary_metric": "pe"},
        "hvie": {"ok": True, "historical_percentile": 72, "regime": "EXPENSIVE"},
        "varie": {"ok": True, "premium_pct": 12.5, "drivers": ["growth", "margins"]},
        "ownership_intel": {"ok": True, "summary": "FII stake stable."},
        "inputs_present": {
            "master": True,
            "financials_annual": True,
            "financials_quarterly": False,
            "ownership": True,
            "corporate_actions": True,
            "valuation_ratios": True,
            "historical_valuation": True,
            "uve": True,
            "hvie": True,
            "varie": True,
            "vpae": True,
        },
    }
    base.update(over)
    return base


def test_health():
    h = health()
    assert h["ok"] is True
    assert h["recommendation_language"] is False
    assert h["vendor_calls"] is False


def test_executive_has_no_recommendation_language():
    sec = executive(_bundle())
    assert sec["ok"] is True
    text = " ".join(sec["findings"]).lower()
    assert "buy" not in text.split()
    assert "sell" not in text.split()
    assert validate_section(sec)["ok"] is True


def test_valuation_consumes_engines():
    sec = valuation(_bundle())
    assert sec["ok"] is True
    assert any("percentile" in f.lower() for f in sec["findings"])
    assert sec["confidence"]["confidence"] in {"High", "Medium", "Low"}


def test_risk_requires_evidence():
    sec = risk(_bundle(hvie={"ok": True, "historical_percentile": 92, "regime": "VERY_EXPENSIVE"}))
    assert any("Valuation Risk" in f for f in sec["findings"])


def test_build_section_and_dossier(monkeypatch):
    monkeypatch.setattr(
        "research_intelligence_engine.composer.load_bundle",
        lambda symbol: _bundle(symbol=symbol),
    )
    monkeypatch.setattr(
        "research_intelligence_engine.composer._persist_summary",
        lambda dossier: None,
    )
    sec = build_section("INFY", "growth")
    assert sec["ok"] is True
    assert sec["section"] == "growth"
    dossier = build_dossier("INFY")
    assert dossier["ok"] is True
    assert dossier["recommendation"] is None
    assert dossier["investment_rating"] is None
    assert "executive" in dossier["sections"]
    assert dossier["research_quality"]["research_confidence"] in {"High", "Medium", "Low"}
    assert validate_dossier(dossier)["ok"] is True


def test_ask_slice_routes_risk(monkeypatch):
    monkeypatch.setattr(
        "research_intelligence_engine.production.build_section",
        lambda symbol, name: {
            "ok": True,
            "summary": "Valuation Risk: percentile elevated.",
            "findings": ["Valuation Risk: percentile elevated."],
            "confidence": {"confidence": "Medium", "score": 0.6},
            "explainability": {"observed": ["hvie"], "derived": [], "inferred": []},
            "evidence": [],
        },
    )
    out = ask_slice("What are the biggest risks in INFY?", symbol="INFY")
    assert out["ok"] is True
    assert out["section"] == "risk"
    assert out["recommendation"] is None if "recommendation" in out else True


def test_dqiv_rejects_buy_language():
    bad = {
        "ok": True,
        "findings": ["This is a clear BUY opportunity."],
        "summary": "BUY now",
        "explainability": {"observed": ["x"], "derived": [], "inferred": []},
        "evidence": [{"source": "test"}],
        "confidence": {"confidence": "High", "score": 0.9},
    }
    assert validate_section(bad)["ok"] is False
