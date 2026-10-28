"""Institutional Coverage Health contract tests."""

from __future__ import annotations

from institutional_coverage_health import health
from institutional_coverage_health.production import (
    _bar,
    _paged_rows,
    _pct,
    _provider_ratio_index,
    coverage_health,
    valuation_covered,
)


def test_health_contract():
    h = health()
    assert h["ok"] is True
    assert h["engine"] == "institutional_coverage_health"
    assert h["version"] == "1.0.0"
    assert h["primary_kpi"] == "valuation_coverage"
    assert h["rule"] == "vpae_applicability_not_pe_presence"
    assert "/v1/valuation/coverage/health" in h["endpoints"]
    assert "valuation methodology" in h["definition"].lower()


def test_pct_and_bar():
    assert _pct(97, 100) == 97.0
    assert _pct(0, 0) == 0.0
    assert len(_bar(95)) == 10
    assert _bar(100).startswith("█")
    assert _bar(0) == "░" * 10


def test_paged_rows_walks_past_store_max_limit(monkeypatch):
    """Regression: first 5k valuation_ratios rows only cover ~295 symbols."""
    calls = []

    def fake_fetch(tab_id, limit=200, offset=0, **kwargs):
        calls.append(offset)
        if offset == 0:
            rows = [
                {"symbol": f"A{i}", "ratio_name": "pe", "company_value": 10, "reported_date": "2026-01-01"}
                for i in range(5000)
            ]
            return {"ok": True, "rows": rows, "total": 6000, "limit": limit, "offset": offset}
        if offset == 5000:
            rows = [
                {"symbol": f"B{i}", "ratio_name": "pe", "company_value": 11, "reported_date": "2026-01-02"}
                for i in range(1000)
            ]
            return {"ok": True, "rows": rows, "total": 6000, "limit": limit, "offset": offset}
        return {"ok": True, "rows": [], "total": 6000, "limit": limit, "offset": offset}

    monkeypatch.setattr(
        "institutional_warehouse.store.fetch",
        fake_fetch,
    )
    rows = _paged_rows("valuation_ratios")
    assert len(rows) == 6000
    assert calls == [0, 5000]

    # Provider index must see symbols from page 2, not stop at page 1.
    idx = _provider_ratio_index()
    assert len(idx) == 6000
    assert "B0" in idx
    assert "A0" in idx


def test_valuation_covered_rules():
    assert valuation_covered({"ok": False}) == (False, "not_in_warehouse")
    assert valuation_covered({"ok": True, "status": "NOT_APPLICABLE"}) == (None, "not_applicable")
    assert valuation_covered({
        "ok": True,
        "status": "INSUFFICIENT_DATA",
        "primary_model": "PE",
        "primary_metric": "pe",
        "coverage": "PARTIAL",
        "metrics": {"pe": {"status": "Applicable"}},
    }) == (False, "insufficient_data")
    assert valuation_covered({
        "ok": True,
        "status": "LOSS_MAKING",
        "primary_model": "EV_SALES",
        "primary_metric": "ev_sales",
        "coverage": "PARTIAL",
        "metrics": {"ev_sales": {"status": "Applicable"}},
    }) == (True, "complete")
    assert valuation_covered({
        "ok": True,
        "status": "BANKING_MODEL",
        "primary_model": "PB",
        "primary_metric": "pb",
        "coverage": "FULL",
        "metrics": {"pb": {"status": "Applicable"}},
    }) == (True, "complete")
    assert valuation_covered({
        "ok": True,
        "status": "VALID",
        "primary_model": "PE",
        "primary_metric": "pe",
        "coverage": "NONE",
        "metrics": {"pe": {"status": "Applicable"}},
    }) == (False, "no_supporting_data")


def test_coverage_health_empty_warehouse(monkeypatch):
    monkeypatch.setattr(
        "institutional_coverage_health.production._load_masters",
        lambda: [],
    )
    monkeypatch.setattr(
        "institutional_coverage_health.production._provider_ratio_index",
        lambda: {},
    )
    monkeypatch.setattr(
        "institutional_coverage_health.production._annual_index",
        lambda: {},
    )
    monkeypatch.setattr(
        "institutional_coverage_health.production._entity_set",
        lambda tab: set(),
    )
    # Clear cache
    import institutional_coverage_health.production as prod

    prod._CACHE["payload"] = None
    prod._CACHE["at"] = 0.0

    out = coverage_health(limit=10, force=True)
    assert out["ok"] is True
    assert out["primary_kpi"] == "valuation_coverage"
    assert out["universe"]["companies"] == 0
    assert out["valuation_coverage"]["pct"] == 0.0
    assert len(out["dashboard"]) == 6
    assert out["language"] == "analysis_only"
    assert "BUY" not in str(out)
    assert "SELL" not in str(out)


def test_coverage_health_with_synthetic_masters(monkeypatch):
    masters = [
        {"symbol": "INFY", "company_name": "Infosys", "sector": "Information Technology", "isin": "INE009A01021"},
        {"symbol": "HDFCBANK", "company_name": "HDFC Bank", "sector": "Financials", "isin": "INE040A01034"},
        {"symbol": "SWIGGY", "company_name": "Swiggy", "sector": "Consumer Discretionary", "isin": "INE00XX00001"},
    ]
    providers = {
        "INFY": {"source": "upstox", "ratios": {"pe": {"company_value": 28}, "pb": {"company_value": 8}}},
        "HDFCBANK": {"source": "upstox", "ratios": {"pb": {"company_value": 2.5}, "roe": {"company_value": 16}}},
    }
    annual = {
        "INFY": {"revenue": 1e11, "pat": 2e10, "equity": 5e10, "ebitda": 3e10, "cash": 1e9},
        "HDFCBANK": {"revenue": 8e10, "pat": 3e10, "equity": 2e11, "ebitda": None, "cash": 5e9},
        "SWIGGY": {"revenue": 5e9, "pat": -1e9, "equity": 2e9, "ebitda": -5e8, "cash": 1e9},
    }

    def fake_evaluate(symbol, record=None):
        sym = str(symbol).upper()
        if sym == "INFY":
            return {
                "ok": True,
                "symbol": sym,
                "primary_model": "PE",
                "primary_metric": "pe",
                "status": "VALID",
                "confidence": "HIGH",
                "coverage": "FULL",
                "unavailable_metrics": [],
                "metrics": {"pe": {"status": "Applicable"}},
                "dqiv": {"status": "PASS"},
                "company": {"name": "Infosys", "sector": "Information Technology", "instrument_type": "EQUITY"},
            }
        if sym == "HDFCBANK":
            return {
                "ok": True,
                "symbol": sym,
                "primary_model": "PB",
                "primary_metric": "pb",
                "status": "BANKING_MODEL",
                "confidence": "HIGH",
                "coverage": "FULL",
                "unavailable_metrics": ["pe"],
                "metrics": {"pb": {"status": "Applicable"}, "pe": {"status": "Hidden"}},
                "dqiv": {"status": "PASS"},
                "company": {"name": "HDFC Bank", "sector": "Financials", "instrument_type": "EQUITY"},
            }
        return {
            "ok": True,
            "symbol": sym,
            "primary_model": "EV_SALES",
            "primary_metric": "ev_sales",
            "status": "LOSS_MAKING",
            "confidence": "MEDIUM",
            "coverage": "PARTIAL",
            "unavailable_metrics": ["pe"],
            "metrics": {
                "ev_sales": {"status": "Applicable"},
                "pe": {"status": "Unavailable", "reason": "Negative earnings"},
            },
            "dqiv": {"status": "WARN"},
            "company": {"name": "Swiggy", "sector": "Consumer Discretionary", "instrument_type": "EQUITY"},
        }

    monkeypatch.setattr(
        "institutional_coverage_health.production._load_masters",
        lambda: masters,
    )
    monkeypatch.setattr(
        "institutional_coverage_health.production._provider_ratio_index",
        lambda: providers,
    )
    monkeypatch.setattr(
        "institutional_coverage_health.production._annual_index",
        lambda: annual,
    )
    monkeypatch.setattr(
        "institutional_coverage_health.production._entity_set",
        lambda tab: {"INFY", "HDFCBANK"} if tab != "research_intelligence" else {"INFY"},
    )
    monkeypatch.setattr(
        "valuation_policy.engine.evaluate",
        fake_evaluate,
    )

    import institutional_coverage_health.production as prod

    prod._CACHE["payload"] = None
    prod._CACHE["at"] = 0.0

    out = coverage_health(limit=10, force=True)
    assert out["ok"] is True
    assert out["valuation_coverage"]["covered"] == 3
    assert out["valuation_coverage"]["expected"] == 3
    assert out["valuation_coverage"]["pct"] == 100.0
    assert out["universe"]["companies"] == 3
    # PE absence for bank / loss-maker must not drive primary KPI below 100
    assert out["primary_kpi"] == "valuation_coverage"
    names = [d["name"] for d in out["dashboard"]]
    assert "Valuation" in names
    assert "Universe" in names
