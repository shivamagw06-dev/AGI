"""Institutional Research Writer V1 — presentation layer after CIO."""

from __future__ import annotations

from institutional_analysts.memory import reset_for_tests as reset_iaf_memory
from institutional_analysts.production import package_for_ask_agi as iaf_package
from investment_committee.store import reset_for_tests as reset_ici_store
from research_writer.language_quality import scrub_leaks
from research_writer.production import health, package_for_ask_agi, quality_gates
from research_writer.schema import IRW_VERSION


LEAKS = (
    "CID",
    "LEO",
    "IRP",
    "DVC",
    "Yahoo",
    "Groww",
    "Finnhub",
    "FMP",
    "IndianAPI",
    "Academy",
    "Company Analysis",
    "Coverage 62%",
    "Knowledge Grade",
)


def setup_function():
    reset_iaf_memory()
    reset_ici_store()


def test_health_and_gates():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == IRW_VERSION
    assert h["presentation_writing_layer_only"] is True
    assert h["sits_after"] == "cio"
    assert "votes" in h["never_changes"]
    g = quality_gates()
    assert g["passed"] is True
    assert g["checks"]["never_mutates_votes"] is True


def test_scrub_leaks():
    text = scrub_leaks("CID LEO Yahoo Groww Coverage 62% Knowledge Grade C N/A")
    low = text.lower()
    for leak in ("cid", "leo", "yahoo", "groww", "coverage 62", "knowledge grade", "n/a"):
        assert leak not in low


def _hdfc_iaf():
    return iaf_package(
        "Should I invest in HDFC Bank?",
        ticker="HDFCBANK",
        company_analysis={
            "ticker": "HDFCBANK",
            "company_name": "HDFC Bank",
            "identity": {"company_name": "HDFC Bank", "business_model": "Universal bank franchise"},
            "business_quality": {
                "business_quality_score": 78,
                "competitive_advantages": ["Distribution scale", "Brand trust"],
                "revenue_drivers": ["Deposit franchise"],
                "confidence": 0.72,
            },
            "financial_intelligence": {
                "trend": "Improving cash conversion",
                "roe": "16%",
                "confidence": 0.7,
            },
            "valuation_intelligence": {
                "pe": 24,
                "pb": 2.6,
                "margin_of_safety": "Modest",
                "confidence": 0.6,
            },
            "risks": ["Credit cycle", "Regulatory capital", "Deposit competition"],
        },
        company_dossier={
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank"},
            "market_data": {"trend": "Constructive bias", "liquidity": "High"},
            "shareholding": {"promoters": "Stable", "trend": "Stable alignment"},
            "management": {"governance": "Institutional-grade board oversight"},
        },
        valuation={"pe": 24, "margin_of_safety": "Modest"},
        sector_intelligence={"sector_id": "private_banks", "growth": "Attractive mid-cycle credit growth"},
        company_monitor={"what_changed": {"risks": ["Deposit competition"], "monitor": ["NIM"]}},
        institutional_briefing={
            "macro_drivers": ["Policy rates"],
            "macro_transmission": "Rates transmit via NIMs and loan demand.",
            "current_outlook": "Macro mildly supportive",
        },
        finance_academy={"applied_concepts": ["Franchise economics"]},
        decision_engine={
            "active": True,
            "layers": [
                {"id": "macro", "score": 62, "reasoning": "Supportive"},
                {"id": "technical", "score": 58, "reasoning": "Constructive tape"},
                {"id": "risk", "score": 42, "reasoning": "Risks live"},
                {"id": "management", "score": 70, "reasoning": "Execution solid"},
            ],
            "summary": {"confidence_pct": 68, "expected_return_12m_pct": 11},
        },
    )


def test_irw_after_cio_publication_quality():
    iaf = _hdfc_iaf()
    assert iaf["enabled"] is True
    assert iaf.get("research_writer", {}).get("enabled") is True
    irw = iaf["research_writer"]
    report = irw["institutional_report"]
    assert report["report_type"]
    assert report["voice"] == "Institutional Equity Research"

    exec_sum = irw["executive_summary"] or ""
    assert "HDFC" in exec_sum
    words = exec_sum.split()
    assert 60 <= len(words) <= 160

    # Interpretive prose — not raw score dumps / price dumps
    biz = irw["business_intelligence"] or ""
    assert "Business Quality 63" not in biz
    assert "78" not in biz or "durable" in biz.lower() or "competitive" in biz.lower()

    fin = irw["financial_intelligence"] or ""
    assert "ROE 18%" not in fin
    assert "value creation" in fin.lower() or "cash" in fin.lower() or "return" in fin.lower()

    val = irw["valuation_intelligence"] or ""
    assert "expectations" in val.lower() or "multiple" in val.lower() or "valuation" in val.lower()

    mkt = irw["market_intelligence"] or ""
    assert "₹" not in mkt

    risks = irw["risk_register"] or []
    assert risks
    assert all(r.get("description") and r.get("monitoring_trigger") for r in risks)

    scenarios = report["sections"]["scenarios"]
    for key in ("bull", "base", "bear"):
        assert scenarios[key]["probability"]
        assert scenarios[key]["assumptions"]
        assert scenarios[key]["investment_implication"]

    conclusion = irw["institutional_conclusion"] or ""
    assert len(conclusion.split()) <= 260

    # Tables / charts recommended when data exists
    assert irw["tables"]
    assert irw["chart_recommendations"]

    # Quality gate
    q = irw["quality"]
    assert q["no_provider_names"] is True
    assert q["no_engine_names"] is True
    assert q["passed"] is True

    joined = " ".join(
        [
            exec_sum,
            biz,
            fin,
            val,
            mkt,
            irw.get("macro_intelligence") or "",
            conclusion,
        ]
    )
    for leak in LEAKS:
        assert leak.lower() not in joined.lower(), f"leaked {leak}"

    # Never mutate intelligence
    unchanged = irw["intelligence_unchanged"]
    assert unchanged.get("committee_vote") == iaf.get("committee_vote")
    assert unchanged.get("confidence") == iaf.get("confidence")


def test_irw_standalone_package():
    iaf = _hdfc_iaf()
    # Strip writer and re-run writer only
    pack = {k: v for k, v in iaf.items() if k not in {"research_writer", "institutional_report", "written_business_intelligence"}}
    pack.pop("research_writer", None)
    out = package_for_ask_agi(pack, query="Should I invest in HDFC Bank?")
    assert out["enabled"] is True
    assert out["executive_summary"]
    assert out["presentation_writing_layer_only"] is True


def test_answer_construction_uses_irw_voice():
    from answer_construction.production import package_for_ask_agi as ac_package

    out = ac_package(
        query="Should I invest in HDFC Bank?",
        ticker="HDFCBANK",
        company_analysis={
            "ticker": "HDFCBANK",
            "company_name": "HDFC Bank",
            "identity": {"company_name": "HDFC Bank", "business_model": "Bank"},
            "business_quality": {"business_quality_score": 78, "confidence": 0.7},
            "financial_intelligence": {"trend": "Improving", "roe": "16%", "confidence": 0.7},
            "valuation_intelligence": {"pe": 24, "margin_of_safety": "Modest"},
            "risks": ["Credit"],
        },
        company_dossier={
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank"},
            "market_data": {"trend": "Constructive", "liquidity": "High"},
            "shareholding": {"promoters": "Stable"},
            "management": {"governance": "Solid"},
        },
        valuation={"pe": 24, "margin_of_safety": "Modest"},
        sector_intelligence={"sector_id": "private_banks", "growth": "Attractive"},
        institutional_briefing={"current_outlook": "Supportive", "macro_drivers": ["Rates"]},
        executive="Placeholder",
        thesis="Placeholder",
        house_label="Neutral",
        bull=[],
        bear=[],
        risks=[],
        catalysts=[],
        why=[],
    )
    assert out["enabled"] is True
    assert out.get("institutional_research_writer_active") is True
    assert out["answer_policy"] == "institutional_research_writer_publication_note"
    assert "HDFC" in (out["executive"] or "")
    assert out.get("research_writer", {}).get("enabled") is True
