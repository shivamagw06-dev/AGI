"""CIO research-note soft-wire — prose, scrubbing, no status-report leaks."""

from __future__ import annotations

from app.ui.sanitize import scrub, scrub_text
from intelligence_construction.cio_prose import (
    business_intelligence_narrative,
    market_intelligence_pack,
    research_takeaways,
    translate_academy_concept,
)
from intelligence_construction.production import package_for_ask_agi


def test_scrub_hides_framework_names():
    assert "CID" not in scrub_text("CID coverage incomplete")
    assert "IRP" not in scrub_text("IRP V1 reasoning")
    assert "LEO" not in scrub_text("LEO gate blocked")
    assert "SIF" not in scrub_text("SIF sector framework")
    out = scrub({"leo_blocked": True, "concept_ids": ["dividend_principle"], "thesis": "Quality compounder"})
    assert "leo_blocked" not in out
    assert "concept_ids" not in out
    assert out["thesis"] == "Quality compounder"


def test_business_intelligence_is_cio_prose():
    biz = business_intelligence_narrative(
        cid={
            "ticker": "ZOMATO",
            "identity": {"company_name": "Eternal", "sector": "Internet", "industry": "Online Services"},
            "business_profile": {"business_model": "a multi-sided consumer internet platform spanning food delivery and quick commerce"},
        },
        company_analysis={
            "identity": {
                "company_name": "Eternal",
                "sector": "Internet",
                "industry": "Online Services",
                "business_model": "a multi-sided consumer internet platform spanning food delivery and quick commerce",
            },
            "risks": ["Competitive intensity and cash-burn risk"],
            "catalysts": ["Next quarterly results"],
            "business_quality": {"business_quality_score": 72, "grade": "B+"},
        },
    )
    assert "business_model" in biz
    assert "Eternal" in biz["business_model"]
    assert "matters because" in biz["business_model"].lower() or "determines how revenue" in biz["business_model"].lower()
    assert "competitive_advantages" in biz
    assert "dividend_principle" not in str(biz).lower()
    assert "CID" not in str(biz)
    assert "unknown" not in str(biz).lower()
    assert "not available" not in str(biz).lower()


def test_market_intelligence_populates_from_cid():
    market = market_intelligence_pack(
        {
            "ticker": "ZOMATO",
            "market_data": {
                "current_price": 245.5,
                "fifty_two_week_high": 300,
                "fifty_two_week_low": 180,
                "market_cap": 2.1e12,
                "currency": "INR",
            },
        },
        {"identity": {"company_name": "Eternal"}},
    )
    assert market["narrative"]
    assert "Eternal" in market["narrative"]
    assert "trade near" in market["narrative"].lower()
    assert market["cards"]
    labels = {c["label"] for c in market["cards"]}
    assert "Price" in labels
    assert "Market Cap" in labels
    assert "52-Week Range" in labels
    assert market["momentum"]


def test_package_reads_like_research_note_not_status_report():
    pkg = package_for_ask_agi(
        "Should I buy Eternal?",
        ticker="ZOMATO",
        cid={
            "ticker": "ZOMATO",
            "identity": {"company_name": "Eternal", "sector": "Internet", "industry": "Online Services"},
            "business_profile": {"business_model": "consumer internet platform for food delivery and quick commerce"},
            "market_data": {
                "current_price": 245,
                "fifty_two_week_high": 300,
                "fifty_two_week_low": 180,
                "market_cap": 2e12,
                "currency": "INR",
            },
        },
        company_analysis={
            "enabled": True,
            "identity": {
                "company_name": "Eternal",
                "business_model": "consumer internet platform for food delivery and quick commerce",
                "sector": "Internet",
                "industry": "Online Services",
            },
            "financial_intelligence": {
                "narrative": "Unit economics are improving as delivery density rises, supporting operating leverage."
            },
            "valuation_intelligence": {
                "narrative": "The multiple embeds high growth expectations and leaves limited room for execution miss.",
                "current_pe": 85,
            },
            "risks": ["Competition and profitability path"],
            "catalysts": ["Earnings print"],
            "business_quality": {"business_quality_score": 74, "grade": "B+"},
        },
        finance_academy={"concept_ids": ["incremental_roic"], "answer_hints": []},
    )
    enrich = pkg["answer_enrichment"]
    exec_sum = enrich["executive_summary"]
    assert "Insufficient" not in exec_sum
    assert "Recommendation withheld" not in exec_sum
    assert "Coverage" not in exec_sum
    assert "CID" not in exec_sum
    assert "IRP" not in exec_sum
    assert "incremental_roic" not in exec_sum
    assert "Eternal" in exec_sum or "consumer internet" in exec_sum.lower()
    assert pkg["sections"]["business_intelligence"]["business_model"]
    assert pkg["sections"]["market_performance"]["cards"]
    takeaways = research_takeaways(
        business=pkg["sections"]["business_intelligence"],
        market=pkg["sections"]["market_performance"],
        financial_n="Unit economics are improving.",
    )
    assert takeaways
    assert not any("assembled" in t.lower() or "attached" in t.lower() for t in takeaways)


def test_translate_academy_never_returns_snake_case_id():
    # Even if teach() fails offline, humanised fallback must not echo the raw id as the whole string.
    out = translate_academy_concept("incremental_roic")
    if out:
        assert out != "incremental_roic"
        assert "incremental_roic" not in out
