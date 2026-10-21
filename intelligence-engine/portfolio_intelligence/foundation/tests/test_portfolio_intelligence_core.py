"""Unit tests for Phase 3.3 Portfolio Intelligence foundation."""

from __future__ import annotations

from portfolio_intelligence.foundation.catalog import get_portfolio, list_portfolio_ids
from portfolio_intelligence.foundation.production import analyse, health, soft_slice_for_ask_agi
from portfolio_intelligence.foundation.schema import ASK_WIRED, RECOMMENDATION_POLICY


def test_health_wired_via_kul():
    h = health()
    assert h["ok"] is True
    assert h["ask_wired"] is True
    assert ASK_WIRED is True
    assert h["ask_wired_via"] == "knowledge_unification.providers.portfolio_intelligence"
    assert h["portfolio_count"] >= 2
    assert "no_buy_sell" in h["recommendation_policy"] or "observations_only" in h["recommendation_policy"]


def test_soft_slice_diagnostics_only():
    out = soft_slice_for_ask_agi("Explain portfolio construction for AGIB Core India Equity.")
    assert out.get("ask_wired") is True
    assert out.get("ask_wired_via") == "knowledge_unification.providers.portfolio_intelligence"


def test_analyse_overview_executive_brief():
    out = analyse("Provide an executive portfolio brief overview.", portfolio_id="agib_core_india")
    assert out["ok"] is True
    assert out["recommendation"] is None
    assert out["recommendation_policy"] == RECOMMENDATION_POLICY
    assert out["portfolio_summary"]
    assert out["diversification"]
    assert out["key_risks"]
    assert out["sector_exposures"]
    assert out["monitoring_priorities"]
    assert out["evidence"]
    assert out["unknowns"]
    assert out["executive_brief_order"][0] == "portfolio_summary"


def test_compare_portfolios():
    out = analyse("Compare AGIB Core India Equity and AGIB Concentrated Growth Book.")
    assert out["ok"] is True
    assert out.get("compare")
    assert "quality" in (out.get("summary") or "").lower() or out["compare"].get("quality_scores")


def test_no_recommendation_leak():
    out = analyse("Which holdings dominate portfolio risk?", portfolio_id="agib_core_india")
    text = (out.get("summary") or "").lower()
    assert "buy" not in text or "no buy" in text or "buy/sell" in text
    assert out["recommendation"] is None


def test_catalog_portfolios():
    assert "agib_core_india" in list_portfolio_ids()
    p = get_portfolio("agib_core_india")
    assert p and len(p["holdings"]) >= 5
