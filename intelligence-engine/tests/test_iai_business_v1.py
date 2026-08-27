"""Institutional Analyst Intelligence V1 — Business Analyst only."""

from __future__ import annotations

from institutional_analysts.business.analyst import analyse
from institutional_analysts.business.brain import IAI_BUSINESS_VERSION, think
from institutional_analysts.business.brain.business_dna import reset_for_tests as reset_dna
from institutional_analysts.business.brain.memory import reset_for_tests as reset_ba_mem
from institutional_analysts.flags import is_iai_business_enabled
from institutional_analysts.memory import put_opinion, reset_for_tests
from institutional_analysts.production import package_for_ask_agi


INTERNAL_LEAKS = (
    "CID",
    "LEO",
    "IRP",
    "Yahoo",
    "Groww",
    "MarketDataClient",
    "Company Analysis",
    "Financial Intelligence",
    "provider",
)


def _ctx(*, biz_score: float = 78) -> dict:
    return {
        "query": "Should I invest in HDFC Bank?",
        "ticker": "HDFCBANK",
        "company_analysis": {
            "enabled": True,
            "ticker": "HDFCBANK",
            "company_name": "HDFC Bank",
            "identity": {"company_name": "HDFC Bank", "business_model": "Universal bank franchise"},
            "business_quality": {
                "business_quality_score": biz_score,
                "revenue_drivers": ["Deposit franchise", "Retail credit"],
                "competitive_advantages": ["Distribution scale", "Brand trust", "Network reach"],
                "pricing_power": "Franchise pricing power in retail liabilities",
                "brand": "High-trust retail franchise",
                "capital_allocation": "Disciplined reinvestment in franchise capacity",
                "confidence": 0.72,
                "risks": ["Deposit competition", "Regulatory change"],
            },
            "investment_thesis": {
                "competitive_advantages": ["Distribution scale", "Brand trust"],
                "risks": ["Credit cycle"],
            },
        },
        "company_dossier": {
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank", "industry": "Private banking"},
            "business_profile": {"business_model": "Universal bank franchise"},
        },
        "finance_academy": {"applied_concepts": ["Franchise economics", "Switching costs"]},
        "live_evidence": {
            "documents_used": ["Annual report commentary"],
            "freshness_score": 0.7,
        },
    }


def setup_function():
    reset_for_tests()
    reset_dna()
    reset_ba_mem()


def test_iai_business_flag_default_on():
    assert is_iai_business_enabled() is True


def test_brain_think_institutional_shape():
    evidence = {
        "company": "HDFC Bank",
        "business_model": "Universal bank franchise",
        "advantages": ["Distribution scale", "Brand trust", "Network reach"],
        "revenue_drivers": ["Deposit franchise", "Retail credit"],
        "competitive_position": "Private banking",
        "pricing_power": "Franchise pricing power",
        "brand": "High-trust retail franchise",
        "capital_allocation": "Disciplined reinvestment",
        "growth_opportunities": ["Share gains"],
        "business_risks": ["Deposit competition"],
        "business_quality_score": 78,
        "evidence_refs": [
            {"claim": "Distribution scale", "source_ref": "institutional research"},
            {"claim": "Annual report commentary", "source_ref": "institutional research"},
        ],
    }
    out = think(
        company="HDFC Bank",
        evidence=evidence,
        confidence={"evidence": 0.7, "knowledge": 0.72, "freshness": 0.7, "overall": 0.7},
    )
    assert out["iai_version"] == IAI_BUSINESS_VERSION
    assert out["stance"] in {"Bullish", "Neutral", "Bearish"}
    assert out["business_quality"]["grade"] in {"Exceptional", "High", "Adequate", "Weak"}
    assert out["moat_assessment"]["durability"] in {
        "High",
        "Moderate",
        "Low",
        "Strong",
        "Medium",
        "Weak",
        "Improving",
        "Declining",
    }
    assert out["competitive_outlook"]["summary"]
    assert len(out["reasoning"]) >= 4
    assert out["assumptions"]
    assert out["uncertainty"]
    assert out["unanswered_questions"]
    assert "quality_checks" in out
    assert "validation" in out
    assert "Porter Five Forces" in out["frameworks_applied"]
    text = " ".join(
        [
            str(out.get("institutional_business_opinion") or ""),
            str(out.get("moat_assessment")),
            str(out.get("reasoning")),
        ]
    )
    for leak in INTERNAL_LEAKS:
        assert leak.lower() not in text.lower()


def test_analyst_emits_richer_opinion_not_summary_only():
    op = analyse(_ctx())
    assert op["role"] == "business"
    assert op.get("iai_active") is True
    assert op.get("iai_version") == IAI_BUSINESS_VERSION
    assert op["structured"] is True
    assert op["institutional_business_opinion"]
    assert isinstance(op["business_quality"], dict)
    assert op["business_quality"].get("grade")
    assert isinstance(op["moat_assessment"], dict)
    assert op["moat_assessment"].get("durability")
    assert isinstance(op["competitive_outlook"], dict)
    assert op["reasoning"]
    assert op["assumptions"]
    assert op["uncertainty"]
    assert op["quality_checks"]
    # Mandate: no valuation language
    blob = " ".join(
        [
            op.get("summary") or "",
            op.get("institutional_business_opinion") or "",
            " ".join(op.get("strengths") or []),
            " ".join(op.get("weaknesses") or []),
        ]
    ).lower()
    for forbidden in ("p/e", "intrinsic", "margin of safety", "overvalued", "undervalued"):
        assert forbidden not in blob


def test_memory_compares_prior_view():
    put_opinion(
        "HDFCBANK",
        "business",
        {
            "summary": "Prior franchise view was cautious.",
            "stance": "Neutral",
            "strengths": ["Brand trust"],
            "weaknesses": ["Competition"],
            "confidence": {"overall": 0.5},
        },
    )
    op = analyse(_ctx(biz_score=80))
    assert op["stance"] in {"Bullish", "Neutral", "Bearish"}
    wc = op.get("what_changed")
    assert wc is not None
    notes = " ".join((wc.get("notes") if isinstance(wc, dict) else []) or [])
    # Either stance shift note or stable note should exist
    assert notes


def test_weak_franchise_bearish_path():
    op = analyse(_ctx(biz_score=35))
    assert op["stance"] in {"Bearish", "Neutral"}
    assert op["moat_assessment"]["durability"] in {
        "Low",
        "Moderate",
        "Weak",
        "Medium",
        "Declining",
    }


def test_package_still_consumes_business_opinion():
    ctx = _ctx()
    pack = package_for_ask_agi(
        ctx["query"],
        ticker=ctx["ticker"],
        company_analysis=ctx["company_analysis"],
        company_dossier=ctx["company_dossier"],
        finance_academy=ctx["finance_academy"],
        live_evidence=ctx["live_evidence"],
    )
    assert pack.get("enabled") is True
    biz = (pack.get("analyst_opinions") or {}).get("business") or {}
    assert biz.get("summary") or biz.get("institutional_business_opinion")
    assert biz.get("iai_active") is True
    assert biz.get("what_changed") is None  # first run
    summary = str(biz.get("summary") or "")
    for leak in ("CID", "LEO", "Yahoo", "MarketDataClient"):
        assert leak not in summary
