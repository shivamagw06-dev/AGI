"""VARIE contract tests — attribution without invented causes."""

from __future__ import annotations

from valuation_attribution_engine import health
from valuation_attribution_engine.evidence import decompose_premium, factor, pct_change
from valuation_attribution_engine.production import company, market, opportunities


def test_health_contract():
    h = health()
    assert h["ok"] is True
    assert h["engine"] == "valuation_attribution_engine"
    assert h["version"] == "1.0.0"
    assert h["rule"] == "no_invented_causes_no_buy_sell_no_ui_calculations"
    assert "/v1/valuation/attribution/company/{symbol}" in h["endpoints"]
    assert h["language"] == "analysis_only"


def test_pct_change_and_decompose():
    assert pct_change(100, 110) == 10.0
    assert pct_change(0, 10) is None
    factors = [
        factor(
            key="roe",
            label="ROE",
            direction="supporting_premium",
            statement="ROE improved",
            evidence_kind="observed",
            strength=0.6,
            source="test",
        ),
        factor(
            key="margin",
            label="Margin",
            direction="supporting_premium",
            statement="Margins expanded",
            evidence_kind="observed",
            strength=0.4,
            source="test",
        ),
    ]
    parts = decompose_premium(20.0, factors)
    assert parts
    assert abs(sum(p["contribution_pct"] for p in parts) - 20.0) < 0.2
    empty = decompose_premium(12.0, [])
    assert empty[0]["key"] == "residual"
    assert "cannot be determined" in empty[0]["statement"].lower()


def test_company_missing_symbol():
    out = company("")
    assert out["ok"] is False
    assert out["error"] == "symbol_required"


def test_company_and_market_empty_universe(monkeypatch):
    empty = {"ok": True, "rows": [], "valuation_date": "2026-08-04"}

    monkeypatch.setattr(
        "valuation_attribution_engine.evidence.load_universe_row",
        lambda symbol, universe_limit=5000: None,
    )
    monkeypatch.setattr(
        "valuation_attribution_engine.evidence.load_warehouse_company",
        lambda symbol: {"ok": False},
    )
    monkeypatch.setattr(
        "valuation_attribution_engine.evidence.load_hvie",
        lambda symbol, metric="pe", window="10y": {"ok": False},
    )
    monkeypatch.setattr(
        "valuation_attribution_engine.evidence.load_hvie_rerating",
        lambda symbol, metric="pe", window="max": {"ok": False},
    )
    monkeypatch.setattr(
        "valuation_attribution_engine.evidence.load_flows",
        lambda: {"ok": True, "available": False},
    )

    out = company("INFY")
    assert out["ok"] is True
    assert out["language"] == "analysis_only"
    assert "cannot be determined" in " ".join(out["why"]).lower() or out["why"]
    assert "BUY" not in (out.get("research_note") or {}).get("body", "")
    assert "SELL" not in (out.get("research_note") or {}).get("body", "")

    monkeypatch.setattr(
        "market_intelligence_engine.universe.load_universe",
        lambda limit=5000: empty,
    )

    def _fake_overview(uni):
        return {"ok": True, "companies": 0, "averages": {}}

    def _fake_table(uni):
        return []

    monkeypatch.setattr("market_intelligence_engine.aggregation.market_overview", _fake_overview)
    monkeypatch.setattr("market_intelligence_engine.aggregation.sector_table", _fake_table)
    m = market()
    assert m["ok"] is True
    assert m["market"] == "Indian Market"

    opps = opportunities()
    assert opps["ok"] is True
    assert "historically_cheap" in opps
