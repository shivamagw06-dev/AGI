"""Ask AGI Intelligence Construction V2 — CID bridge + institutional brief."""

from __future__ import annotations

from company_analysis.cid_bridge import (
    market_snapshot,
    normalise_financials,
    normalise_valuation,
    unwrap_validated,
)
from company_analysis.financial import analyse_financials
from company_analysis.identity import identify_company
from company_analysis.valuation_intel import analyse_valuation
from intelligence_construction.production import health, package_for_ask_agi, quality_gates
from intelligence_construction.schema import IC_VERSION
from app.ui.sanitize import scrub, scrub_text


def test_health_and_gates():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == IC_VERSION
    assert h["never_expose_providers"] is True
    g = quality_gates()
    assert g["passed"] is True


def test_cid_bridge_reads_yahoo_shaped_fields():
    cid = {
        "ticker": "HDFCBANK",
        "identity": {"company_name": "HDFC Bank", "sector": "Banks", "industry": "Private Banks"},
        "business_profile": {"business_model": "Retail and wholesale banking franchise"},
        "financial_metrics": {
            "roe": 0.17,
            "operating_margin": 0.24,
            "revenue_growth": 0.12,
            "profit_margin": 0.18,
            "free_cash_flow": 1.2e11,
        },
        "valuation": {
            "current": {
                "trailing_pe": 18.5,
                "forward_pe": 16.2,
                "price_to_book": 2.8,
                "peg": 1.1,
                "ev_ebitda": 12.0,
            }
        },
        "market_data": {
            "current_price": 1650,
            "fifty_two_week_high": 1800,
            "fifty_two_week_low": 1400,
            "market_cap": 1.2e13,
            "currency": "INR",
            "valuation_multiples": {"trailing_pe": 18.5},
        },
        "peer_comparison": {"ownership": {"institutions_percent": 72.5, "insiders_percent": 0.1}},
        "financial_history": {"kpi_trends": {"roe": [0.15, 0.16, 0.17], "revenue_growth": [0.08, 0.1, 0.12]}},
        "validated_fields": {"pe": {"value": 18.5, "provider": "yahoo"}},
    }

    fin = normalise_financials(cid)
    assert fin["roe"] == 0.17
    assert fin["net_margin"] == 0.18
    assert fin["fcf"] == 1.2e11

    val = normalise_valuation(cid)
    assert val["pe"] == 18.5
    assert val["pb"] == 2.8
    assert val["forward_pe"] == 16.2

    assert unwrap_validated(cid["validated_fields"])["pe"] == 18.5
    snap = market_snapshot(cid)
    assert snap["range_position_0_1"] is not None
    assert 0.5 < snap["range_position_0_1"] < 1.0

    identity = identify_company("HDFCBANK", cid=cid, sif_pkg={"sector_id": "banks"})
    assert "banking" in (identity.get("business_model") or "").lower() or "bank" in (
        identity.get("business_model") or ""
    ).lower()

    financial = analyse_financials(identity=identity, cid=cid)
    assert financial["enabled"] is True
    assert financial["returns"] == 0.17
    assert financial["coverage_pct"] >= 40
    assert "capital returns" in (financial.get("narrative") or "").lower() or "return" in (
        financial.get("narrative") or ""
    ).lower()

    valuation = analyse_valuation(identity=identity, cid=cid)
    assert valuation["current_pe"] == 18.5
    assert valuation["pb"] == 2.8
    assert valuation["forward_pe"] == 16.2
    assert "pe" in (valuation.get("narrative") or "").lower()


def test_brief_never_mentions_yahoo_and_enriches_why():
    cid = {
        "ticker": "INFY",
        "identity": {"company_name": "Infosys", "sector": "IT Services"},
        "financial_metrics": {"roe": 0.28, "revenue_growth": 0.09, "operating_margin": 0.21},
        "valuation": {"current": {"trailing_pe": 24.0, "price_to_book": 7.0}},
        "market_data": {
            "current_price": 1600,
            "fifty_two_week_high": 1700,
            "fifty_two_week_low": 1300,
            "currency": "INR",
        },
        "peer_comparison": {"ownership": {"institutions_percent": 65.0}},
        "enrichment": {"yahoo": {"provider_id": "yahoo"}},
    }
    ca = {
        "enabled": True,
        "identity": {"company_name": "Infosys", "ticker": "INFY", "sector": "IT Services"},
        "financial_intelligence": analyse_financials(
            identity={"ticker": "INFY", "sector": "IT", "sector_id": "it"},
            cid=cid,
        ),
        "valuation_intelligence": analyse_valuation(
            identity={"ticker": "INFY", "sector": "IT", "sector_id": "it"},
            cid=cid,
        ),
        "business_quality": {"business_quality_score": 78, "grade": "B"},
        "investment_thesis": "Infosys remains a high-quality IT franchise with durable returns.",
        "ask_agi_hints": ["Quality franchise with institutional ownership support."],
        "risks": ["Client spending slowdown"],
        "catalysts": ["Large deal wins"],
    }
    brief = package_for_ask_agi(
        "Should I invest in Infosys?",
        ticker="INFY",
        cid=cid,
        company_analysis=ca,
        company_monitor={"enabled": True, "ask_agi_hints": ["No material adverse change since prior snapshot."]},
        finance_academy={"answer_hints": ["ROIC and cash conversion matter for software services."]},
    )
    assert brief["enabled"] is True
    assert brief["version"] == IC_VERSION
    enrich = brief["answer_enrichment"]
    assert enrich["why_bullets"]
    blob = " ".join(
        enrich["why_bullets"]
        + [enrich.get("executive_summary") or "", enrich.get("valuation_perspective") or ""]
    ).lower()
    assert "yahoo" not in blob
    assert "yfinance" not in blob
    assert "finnhub" not in blob
    assert "quoteSummary".lower() not in blob
    assert "indianapi" not in blob

    cleaned = scrub(brief)
    assert "enrichment" not in cleaned
    assert "yahoo" not in str(cleaned.get("sections") or {}).lower()
    scrubbed = scrub_text("Powered by Yahoo Finance quoteSummary via yfinance") or ""
    assert "yahoo" not in scrubbed.lower()
    assert "institutional data" in scrubbed.lower()
