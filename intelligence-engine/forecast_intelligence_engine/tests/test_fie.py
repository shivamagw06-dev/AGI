"""Forecast Intelligence Engine — consumer tests, no recommendations."""

from __future__ import annotations

from forecast_intelligence_engine import ask_slice, health
from forecast_intelligence_engine import production
from forecast_intelligence_engine.composer import build_forecast, build_module
from forecast_intelligence_engine.dqiv import validate_pack, validate_section
from forecast_intelligence_engine.modules import executive, scenarios, valuation
from forecast_intelligence_engine.trend import scenario_probabilities


def _bundle(**over):
    base = {
        "symbol": "INFY",
        "master": {"symbol": "INFY", "company_name": "Infosys", "sector": "IT", "industry": "IT Services"},
        "annual": [
            {
                "fiscal_year": "FY23", "revenue": 140000, "pat": 23000, "eps": 45,
                "ebitda": 35000, "ebit": 32000, "equity": 70000, "debt": 2000, "cash": 5000,
                "cfo": 22000, "free_cash_flow": 18000, "gross_profit": 50000,
            },
            {
                "fiscal_year": "FY24", "revenue": 150000, "pat": 25000, "eps": 48,
                "ebitda": 38000, "ebit": 34000, "equity": 80000, "debt": 1800, "cash": 6000,
                "cfo": 24000, "free_cash_flow": 20000, "gross_profit": 54000,
            },
            {
                "fiscal_year": "FY25", "revenue": 165000, "pat": 27000, "eps": 52,
                "ebitda": 42000, "ebit": 37000, "equity": 90000, "debt": 1500, "cash": 7000,
                "cfo": 26000, "free_cash_flow": 22000, "gross_profit": 60000,
            },
        ],
        "quarterly": [{"fiscal_period": "FY26Q1", "revenue": 42000, "pat": 7000}],
        "historical_valuation": [{"date": "2026-01-01", "pe": 24, "pb": 7}],
        "historical_statistics": [],
        "valuation_ratios": [{"roe": 30, "roce": 35}],
        "ownership": [],
        "corporate_actions": [{"date": "2025-06-01", "action_type": "dividend"}],
        "research_timeline": [{"date": "2026-01-15", "event": "valuation_regime_changed"}],
        "forecast_history": [],
        "forecast_accuracy": [],
        "latest_annual": {
            "fiscal_year": "FY25", "revenue": 165000, "pat": 27000, "eps": 52,
            "ebitda": 42000, "equity": 90000, "debt": 1500, "cash": 7000,
        },
        "prev_annual": {"fiscal_year": "FY24", "revenue": 150000, "pat": 25000},
        "uve": {"ok": True, "primary_model": "PE"},
        "vpae": {"ok": True, "primary_model": "PE", "primary_metric": "pe"},
        "hvie": {"ok": True, "historical_percentile": 72, "regime": "EXPENSIVE"},
        "varie": {"ok": True, "premium_pct": 12.5},
        "rie": {"ok": True, "research_quality": {"research_confidence": "High", "score": 0.8}, "sections": {}},
        "inputs_present": {
            "master": True,
            "financials_annual": True,
            "financials_quarterly": True,
            "historical_valuation": True,
            "uve": True,
            "hvie": True,
            "varie": True,
            "vpae": True,
            "rie": True,
        },
    }
    base.update(over)
    return base


def test_health():
    h = health()
    assert h["ok"] is True
    assert h["recommendation_language"] is False
    assert h["vendor_calls"] is False
    assert h["target_prices"] is False
    assert h["version"] == "8.5"


def test_probabilities_sum_100():
    probs = scenario_probabilities(stability=0.7, confidence_score=0.6)
    assert abs(probs["bull"] + probs["base"] + probs["bear"] - 100.0) < 0.2


def test_executive_no_recommendation_language():
    sec = executive(_bundle())
    assert sec["ok"] is True
    text = " ".join(sec["findings"]).lower()
    assert "buy" not in text.split()
    assert "sell" not in text.split()
    assert "target price" not in text
    assert validate_section(sec)["ok"] is True


def test_valuation_outlook_has_no_target_price():
    sec = valuation(_bundle())
    assert sec["ok"] is True
    assert sec.get("outlook", {}).get("target_price") is None
    assert any("percentile" in f.lower() or "valuation" in f.lower() for f in sec["findings"])


def test_scenarios_probabilities_validated():
    sec = scenarios(_bundle())
    assert sec["ok"] is True
    probs = sec["probabilities"]
    assert abs(probs["bull"] + probs["base"] + probs["bear"] - 100.0) < 0.2
    assert validate_section(sec)["ok"] is True


def test_build_module_and_forecast(monkeypatch):
    monkeypatch.setattr(
        "forecast_intelligence_engine.composer.load_bundle",
        lambda symbol: _bundle(symbol=symbol),
    )
    monkeypatch.setattr(
        "forecast_intelligence_engine.persist.persist_forecast",
        lambda pack: {"ok": True},
    )
    sec = build_module("INFY", "growth")
    assert sec["ok"] is True
    assert sec["module"] == "growth"
    pack = build_forecast("INFY")
    assert pack["ok"] is True
    assert pack["recommendation"] is None
    assert pack["target_price"] is None
    assert pack["investment_rating"] is None
    assert "executive" in pack["modules"]
    assert pack["forecast_quality"]["forecast_confidence"] in {"High", "Medium", "Low"}
    assert validate_pack(pack)["ok"] is True


def test_forecast_fails_closed_when_vintage_persistence_fails(monkeypatch):
    monkeypatch.setattr(
        "forecast_intelligence_engine.composer.load_bundle",
        lambda symbol: _bundle(symbol=symbol),
    )
    monkeypatch.setattr(
        "forecast_intelligence_engine.persist.persist_forecast",
        lambda pack: {"ok": False, "error": "prediction_persistence_failed"},
    )
    pack = build_forecast("INFY")
    assert pack["ok"] is False
    assert pack["status"] == "PERSISTENCE_FAILED"
    assert pack["error"] == "prediction_persistence_failed"


def test_ask_slice_routes_scenarios(monkeypatch):
    monkeypatch.setattr(
        "forecast_intelligence_engine.production.build_module",
        lambda symbol, name: {
            "ok": True,
            "summary": "Bull 25 / Base 55 / Bear 20.",
            "findings": ["Bull 25 / Base 55 / Bear 20."],
            "confidence": {"confidence": "Medium", "score": 0.6},
            "explainability": {"observed": ["cagr"], "derived": [], "assumed": ["multipliers"]},
            "evidence": [],
        },
    )
    out = ask_slice("Explain the bull case for INFY", symbol="INFY")
    assert out["ok"] is True
    assert out["module"] == "scenarios"
    assert out["recommendation"] is None


def test_dqiv_rejects_buy_language():
    bad = {
        "ok": True,
        "findings": ["We recommend a buy on growth acceleration."],
        "summary": "buy now",
        "explainability": {"observed": ["x"], "derived": [], "assumed": []},
        "confidence": {"confidence": "High", "score": 0.9},
        "evidence": [{"source": "x"}],
    }
    assert validate_section(bad)["ok"] is False


def test_dqiv_rejects_forecast_when_verified_history_is_too_thin():
    pack = {
        "modules": {"executive": executive(_bundle())},
        "forecast_quality": {"recommendation": None, "investment_rating": None, "target_price": None},
        "inputs_present": {"financials_annual": True},
        "data_readiness": {
            "forecast_ready": False,
            "failures": ["quarterly_history_below_8_periods"],
        },
        "recommendation": None,
        "investment_rating": None,
        "target_price": None,
    }
    result = validate_pack(pack)
    assert result["ok"] is False
    assert "data_readiness:quarterly_history_below_8_periods" in result["errors"]


def test_company_get_reads_materialised_forecast(monkeypatch):
    calls = []

    def fake_rows(tab, symbol, *, limit=50):
        calls.append((tab, symbol, limit))
        if tab == "forecast_company":
            return ([{
                "symbol": "INFY", "status": "PASS", "as_of": "2026-08-11",
                "executive_summary": "Base case remains most likely.",
                "forecast_confidence": "High", "score": 0.82, "coverage_pct": 91,
                "bull_pct": 25, "base_pct": 55, "bear_pct": 20,
                "modules_ok": 10, "dqiv": "PASS", "version": "8.5",
            }], 1)
        return ([], 0)

    monkeypatch.setattr(production, "_stored_rows", fake_rows)
    monkeypatch.setattr(
        production,
        "build_forecast",
        lambda _symbol: (_ for _ in ()).throw(AssertionError("HTTP path rebuilt forecast")),
    )
    out = production.company("infy")
    assert out["ok"] is True
    assert out["cached"] is True
    assert out["probabilities"] == {"bull": 25, "base": 55, "bear": 20}
    assert calls[0] == ("forecast_company", "INFY", 1)


def test_company_get_reports_not_ready_without_computing(monkeypatch):
    monkeypatch.setattr(production, "_stored_rows", lambda *_a, **_k: ([], 0))
    out = production.company("NEWCO")
    assert out["ok"] is False
    assert out["status"] == "NOT_READY"
    assert out["retryable"] is True


def test_runtime_will_not_start_inside_web_process(monkeypatch):
    from forecast_intelligence_engine import runtime

    monkeypatch.setenv("AGI_ROLE", "web")
    out = runtime.start()
    assert out["ok"] is False
    assert out["reason"] == "forecast_runtime_owned_by_gather_worker"
    assert runtime.status()["runtime"]["status"] == "external_worker"
