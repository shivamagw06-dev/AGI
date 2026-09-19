"""Institutional Analyst Intelligence — Valuation Analyst V1."""

from __future__ import annotations

from institutional_analysts.flags import is_iai_valuation_enabled
from institutional_analysts.memory import reset_for_tests
from institutional_analysts.production import package_for_ask_agi
from institutional_analysts.valuation.analyst import analyse
from institutional_analysts.valuation.brain import IAI_VALUATION_VERSION, think
from institutional_analysts.valuation.brain.memory import reset_for_tests as reset_va_mem
from institutional_analysts.valuation.brain.valuation_dna import reset_for_tests as reset_dna


REQUIRED = (
    "executive_opinion",
    "intrinsic_value_view",
    "market_expectations",
    "valuation_quality",
    "multiple_analysis",
    "dcf_discussion",
    "relative_valuation",
    "historical_valuation",
    "margin_of_safety",
    "valuation_dna",
    "historical_trend",
    "peer_comparison",
    "assumptions",
    "uncertainties",
    "missing_evidence",
    "confidence",
    "quality_checks",
)

FORBIDDEN = (
    "moat",
    "brand strength",
    "management quality",
    "the stock is expensive",
    "the stock is cheap",
    "pe =",
)


def _evidence(**overrides):
    base = {
        "company": "HDFC Bank",
        "ticker": "HDFCBANK",
        "pe": 18.5,
        "forward_pe": 16.8,
        "pb": 2.6,
        "margin_of_safety": "Modest",
        "narrative": "Trades near historical mid-band versus growth.",
        "peer_comparison": "Peer multiples used as a cross-check versus private-bank set",
        "historical": "Near historical mid-band",
        "expected_return": 11,
        "indian_peers": ["Private bank peers"],
        "global_peers": ["Global bank franchises"],
        "growth_context": "Improving cash conversion",
        "capital_efficiency_context": "ROE 16%",
        "evidence_refs": [
            {"claim": "Peer and history triangulation", "source_ref": "institutional research"},
            {"claim": "Current valuation cross-checks", "source_ref": "institutional research"},
        ],
    }
    base.update(overrides)
    return base


def setup_function():
    reset_for_tests()
    reset_dna()
    reset_va_mem()


def test_flag_and_version():
    assert is_iai_valuation_enabled() is True
    assert IAI_VALUATION_VERSION == "iai-valuation-v1.0.0"


def test_think_structured_contract_and_interpretation():
    out = think(
        company="HDFC Bank",
        evidence=_evidence(),
        confidence={"evidence": 0.62, "knowledge": 0.62, "freshness": 0.55, "overall": 0.6},
        ticker="HDFCBANK",
    )
    assert out["iai_version"] == IAI_VALUATION_VERSION
    structured = out["structured_valuation_opinion"]
    for key in REQUIRED:
        assert key in structured, key
    assert "Market Expectations" in out["frameworks_applied"]
    assert out["valuation_dna"]["profile"]
    assert out["case_studies"]["resemblance"]
    assert out["benchmarks"]["never_self_only"] is True
    assert "valuation_coverage" in out["confidence"]
    assert "reasoning" in out["confidence"]

    text = (out.get("executive_opinion") or "").lower()
    for tok in FORBIDDEN:
        assert tok not in text
    assert "expectation" in text or "multiple" in text or "growth" in text
    assert out["stance"] in {"Bullish", "Neutral", "Bearish"}
    # Modest MOS + pe 18.5 should not force bullish cheapness language
    assert "cheap" not in text


def test_premium_multiple_why_language():
    out = think(company="Premium Co", evidence=_evidence(pe=42, forward_pe=38, margin_of_safety="Rich"), ticker="PREM")
    eo = out["executive_opinion"].lower()
    assert "premium" in eo or "embedded" in eo or "expectation" in eo
    assert "pe = 42" not in eo
    assert out["stance"] == "Bearish"


def test_forward_pe_example_quality():
    out = think(company="HDFC Bank", evidence=_evidence(forward_pe=28, pe=30, margin_of_safety="Thin"), ticker="HDFCBANK")
    eo = out["executive_opinion"].lower()
    assert "forward" in eo or "expectation" in eo or "growth" in eo
    assert "forward pe is 28x" not in eo


def test_incomplete_assessment():
    out = think(
        company="Thin Co",
        evidence={"company": "Thin Co", "pe": None, "margin_of_safety": "", "evidence_refs": []},
        confidence={"evidence": 0.2, "knowledge": 0.2, "freshness": 0.2},
    )
    assert out["quality_checks"]["incomplete"] is True
    assert "Incomplete Valuation Assessment" in (out["executive_opinion"] or "")


def test_analyse_soft_wire_domain_guard():
    op = analyse(
        {
            "ticker": "HDFCBANK",
            "company_analysis": {
                "company_name": "HDFC Bank",
                "valuation_intelligence": {
                    "pe": 18.5,
                    "pb": 2.6,
                    "margin_of_safety": "Modest",
                    "narrative": "Trades near historical mid-band versus growth.",
                    "confidence": 0.62,
                },
                "financial_intelligence": {"roe": "16%", "trend": "Improving cash conversion"},
            },
            "valuation": {"pe": 18.5, "pb": 2.6, "margin_of_safety": "Modest"},
            "data_validation": {"confidence": 0.68, "freshness": 0.55},
            "decision_engine": {"summary": {"expected_return_12m_pct": 11, "confidence_pct": 68}},
        }
    )
    assert op.get("iai_valuation_v1") is True
    assert op["role"] == "valuation"
    assert op["executive_opinion"]
    assert isinstance(op["valuation_dna"], dict)
    blob = (op.get("summary") or "").lower() + " " + (op.get("executive_opinion") or "").lower()
    for tok in ("moat", "brand strength", "the stock is expensive", "the stock is cheap"):
        assert tok not in blob


def test_package_consumes_valuation_opinion():
    pack = package_for_ask_agi(
        "Should I invest in HDFC Bank?",
        ticker="HDFCBANK",
        company_analysis={
            "company_name": "HDFC Bank",
            "business_quality": {"business_quality_score": 78, "confidence": 0.7},
            "financial_intelligence": {
                "narrative": "Earnings quality supported by NIMs and fee income.",
                "trend": "Improving cash conversion",
                "roe": "16%",
                "confidence": 0.7,
            },
            "valuation_intelligence": {
                "pe": 18.5,
                "pb": 2.6,
                "margin_of_safety": "Modest",
                "narrative": "Trades near historical mid-band versus growth.",
                "confidence": 0.62,
            },
        },
        valuation={"pe": 18.5, "pb": 2.6, "margin_of_safety": "Modest"},
        company_dossier={"identity": {"company_name": "HDFC Bank"}},
        data_validation={"confidence": 0.68, "checks": ["Statements validated"]},
        decision_engine={"summary": {"expected_return_12m_pct": 11, "confidence_pct": 68}},
    )
    val = (pack.get("analyst_opinions") or {}).get("valuation") or {}
    assert val.get("summary") or val.get("executive_opinion")
    assert val.get("iai_valuation_v1") is True
    # Quality vs entry conflict path still available when biz bullish + val cautious
    assert val.get("stance") in {"Bullish", "Neutral", "Bearish"}
