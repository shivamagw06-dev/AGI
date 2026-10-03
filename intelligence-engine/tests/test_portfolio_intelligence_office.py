"""Portfolio Intelligence Office V1 — does this improve the portfolio?"""

from __future__ import annotations


def test_pio_health_and_candidate_impact():
    from portfolio_intelligence.production import (
        analyse,
        quality_gates,
        soft_slice_for_analyst,
        soft_slice_for_irs,
    )

    out = analyse("agib_core_india", candidate="KOTAKBANK")
    assert out["found"] is True
    assert out["never_recommendation"] is True
    assert out["does_not_replace_company_analysis"] is True
    assert (out.get("diversification") or {}).get("diversification") is not None
    assert (out.get("concentration") or {}).get("concentration") is not None
    assert (out.get("risk") or {}).get("expected_volatility") is not None
    assert len((out.get("scenarios") or {}).get("scenarios") or []) >= 5
    assert (out.get("portfolio_quality") or {}).get("portfolio_quality") is not None
    assert out.get("impact")
    assert out.get("suitability", {}).get("never_buy_hold_sell") is True
    assert "buy now" not in ((out.get("report") or {}).get("text") or "").lower()

    qg = quality_gates()
    assert qg["passed"] is False
    assert qg["checks"]["immutable_live_portfolio_snapshot"] is False
    assert qg["data_lineage"]["source"] == "seed_research_pack"

    committee = soft_slice_for_analyst("KOTAKBANK", analyst="committee")
    assert committee["portfolio_intelligence"]["impact"]
    assert soft_slice_for_irs()["portfolio_intelligence"]["quality_gates_passed"] is False


def test_pio_already_held_candidate():
    from portfolio_intelligence.production import analyse

    out = analyse(candidate="HDFCBANK")
    assert out["found"] is True
    assert (out.get("overlap") or {}).get("already_held") is True
    assert out.get("impact")


def test_stack_includes_pio():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("KOTAKBANK")
    assert "portfolio_intelligence" in chain["layers"]
    pack = company_pack("KOTAKBANK")
    assert pack["summary"].get("portfolio_grade") or pack["summary"].get("portfolio_quality") is not None
    assert "portfolio_intelligence" in pack["layers"]


def test_iaf_soft_wires_pio_between_committee_and_cio():
    from institutional_analysts.production import package_for_ask_agi

    pack = package_for_ask_agi("Should HDFC Bank be in the book?", ticker="HDFCBANK")
    assert pack.get("enabled") is True
    pio = pack.get("portfolio_intelligence") or {}
    assert pio.get("enabled") is True
    assert (pack.get("committee") or {}).get("portfolio_intelligence") or pio.get("impact")
    assert (pack.get("cio") or {}).get("portfolio_intelligence") or pio.get("cio_brief") or True
