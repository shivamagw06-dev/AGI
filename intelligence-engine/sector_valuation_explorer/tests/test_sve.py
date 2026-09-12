"""Institutional Valuation Research Workspace v2 contract tests."""

from __future__ import annotations

from sector_valuation_explorer import health
from sector_valuation_explorer.production import (
    _canonical_sector,
    _enrich_company,
    _industry_medians,
    _sector_explanation,
    market,
    opportunities,
    premium_board,
    rerating_board,
)
from sector_valuation_explorer.status import opportunity_label, outcome_label, valuation_status
from valuation_terminal.sector_lens import lens_for


def test_health_contract():
    h = health()
    assert h["ok"] is True
    assert h["engine"] == "sector_valuation_explorer"
    assert h["version"] == "2.0.0"
    assert "Financials" in h["sectors"]
    assert h["rule"] == "no_ui_calculations_no_buy_sell"
    assert "/v1/valuation/market" in h["endpoints"]
    assert "/v1/valuation/opportunities" in h["endpoints"]
    assert "/v1/valuation/sector/{sector}/industries" in h["endpoints"]


def test_canonical_sector_aliases():
    assert _canonical_sector("information technology") == "Information Technology"
    assert _canonical_sector("Healthcare") == "Health Care"
    assert _canonical_sector("nope") is None


def test_valuation_status_labels():
    assert valuation_status(percentile=10, premium_pct=None, primary_value=12) == "Historically Cheap"
    assert valuation_status(percentile=90, premium_pct=None, primary_value=40) == "Historically Expensive"
    assert valuation_status(percentile=50, premium_pct=0, primary_value=20) == "Fairly Valued"
    assert valuation_status(percentile=None, premium_pct=None, primary_value=None) == "Data Insufficient"
    assert valuation_status(
        percentile=50, premium_pct=0, primary_value=1, policy_status="METRIC_NOT_APPLICABLE",
    ) == "Metric Not Applicable"


def test_opportunity_and_outcome():
    assert opportunity_label(20) == "Attractive"
    assert opportunity_label(80) == "Premium"
    assert "Expensive" in outcome_label(85, 20) or "Premium" in outcome_label(85, 20)


def test_sector_explanation_reuses_lens():
    lens = lens_for("it_services", "Information Technology")
    expl = _sector_explanation(lens, "Information Technology")
    assert expl["primary_metric"] == "pe"
    assert expl["source"] == "valuation_terminal.sector_lens"
    assert any(h["metric"] == "pb" for h in expl["hidden"])


def test_enrich_company_status():
    row = _enrich_company(
        {
            "symbol": "INFY",
            "company_name": "Infosys",
            "sector": "Information Technology",
            "industry": "IT Services",
            "primary_metric": "pe",
            "primary_value": 28,
            "pe": 28,
            "pb": 8,
            "roe": 30,
            "percentile": 82,
            "sector_premium_pct": 18,
            "provider_coverage": 5,
            "market_cap": 5e12,
            "source": "upstox",
        },
        {"median_pe": 24, "median_pb": 6},
        {"IT Services": {"median_pe": 26, "median_pb": 7}},
    )
    assert row["valuation_status"] == "Premium"
    assert row["market_cap_bucket"] == "large"
    assert row["sector_pe"] == 24
    assert row["industry_pe"] == 26
    assert row["historical_regime"] == "Premium"


def test_industry_medians():
    out = _industry_medians([
        {"industry": "IT Services", "sector": "Information Technology", "pe": 28, "pb": 8, "roe": 30, "percentile": 80, "provider_coverage": 3, "market_cap": 1e12},
        {"industry": "IT Services", "sector": "Information Technology", "pe": 24, "pb": 6, "roe": 22, "percentile": 60, "provider_coverage": 2, "market_cap": 5e11},
        {"industry": "Software Products", "sector": "Information Technology", "pe": 40, "pb": 10, "roe": 18, "percentile": 90, "provider_coverage": 1, "market_cap": 2e11},
    ])
    assert out["IT Services"]["companies"] == 2
    assert out["IT Services"]["median_pe"] == 26.0
    assert "Software Products" in out
    # Must not treat peer-rank median (~70 here) as historical own-history %.
    assert out["IT Services"]["historical_percentile"] is None
    assert out["IT Services"]["historical_percentile_status"] == "INSUFFICIENT_HISTORY"
    assert out["IT Services"]["peer_relative_percentile_median"] == 70.0


def test_market_and_boards_empty_universe(monkeypatch):
    empty = {"ok": True, "rows": [], "valuation_date": "2026-08-04"}

    def _fake_load(limit=5000):
        return empty

    monkeypatch.setattr(
        "sector_valuation_explorer.production._load_universe",
        _fake_load,
    )
    m = market()
    assert m["ok"] is True
    assert m["market"] == "Indian Market"
    assert m["companies_covered"] == 0
    assert m["language"] == "analysis_only"
    assert "valuation_coverage_pct" in m
    assert "legacy_pe_or_provider_coverage_pct" in m
    assert "vpae" in (m.get("coverage_definition") or "").lower()

    opps = opportunities(top=5)
    assert opps["ok"] is True
    assert "boards" in opps
    assert "most_attractive" in opps["boards"]

    prem = premium_board(top=5)
    assert prem["ok"] is True
    assert prem["rows"] == []

    re = rerating_board(top=5)
    assert re["ok"] is True
    assert re["rows"] == []
