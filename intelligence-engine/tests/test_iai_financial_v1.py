"""Institutional Analyst Intelligence — Financial Analyst V1."""

from __future__ import annotations

import re

from institutional_analysts.financial.analyst import analyse
from institutional_analysts.financial.brain import IAI_FINANCIAL_VERSION, think
from institutional_analysts.financial.brain.financial_dna import reset_for_tests as reset_dna
from institutional_analysts.financial.brain.memory import reset_for_tests as reset_fa_mem
from institutional_analysts.flags import is_iai_financial_enabled
from institutional_analysts.memory import reset_for_tests
from institutional_analysts.production import package_for_ask_agi


REQUIRED = (
    "executive_opinion",
    "financial_quality",
    "profitability",
    "growth_quality",
    "earnings_quality",
    "cash_flow",
    "balance_sheet",
    "capital_allocation",
    "financial_dna",
    "historical_trend",
    "benchmarking",
    "assumptions",
    "uncertainties",
    "missing_evidence",
    "confidence",
    "quality_checks",
)

LAZY = ("revenue grew", "revenue increased", "margins improved", "debt reduced", "roe increased")
FORBIDDEN = ("moat", "brand", "pricing power", "p/e", "intrinsic", "margin of safety", "macro", "gdp")


def _evidence(**overrides):
    base = {
        "company": "HDFC Bank",
        "ticker": "HDFCBANK",
        "revenue": "Franchise revenue trajectory constructive",
        "margins": "Operating margins resilient with selective pressure",
        "ebitda": "Operating profit supported by core NII and fees",
        "ebit": "EBIT trajectory improving with scale",
        "net_profit": "PAT supported by operating profitability",
        "cash_flow": "Improving cash conversion versus accounting profit",
        "roe": "18",
        "roic": "Improving returns on capital",
        "debt": "Leverage within conservative franchise norms",
        "working_capital": "Working capital intensity stable for the model",
        "capital_allocation": "Disciplined reinvestment and conservative capital posture",
        "financial_quality": "High quality — track cash conversion and return on capital",
        "trend": "Improving cash conversion",
        "narrative": "Earnings quality supported by NIMs and fee income with improving cash conversion.",
        "monitors": ["Cash conversion confirmation", "Liability cost trajectory"],
        "validation_checks": ["Statements validated"],
        "evidence_refs": [
            {"claim": "Improving cash conversion", "source_ref": "institutional research"},
            {"claim": "ROE supported by operating profitability", "source_ref": "institutional research"},
        ],
    }
    base.update(overrides)
    return base


def setup_function():
    reset_for_tests()
    reset_dna()
    reset_fa_mem()


def test_flag_and_version():
    assert is_iai_financial_enabled() is True
    assert IAI_FINANCIAL_VERSION == "iai-financial-v1.0.0"


def test_think_structured_contract_and_why_language():
    out = think(
        company="HDFC Bank",
        evidence=_evidence(),
        confidence={"evidence": 0.7, "knowledge": 0.72, "freshness": 0.68, "overall": 0.7},
        ticker="HDFCBANK",
    )
    assert out["iai_version"] == IAI_FINANCIAL_VERSION
    structured = out["structured_financial_opinion"]
    for key in REQUIRED:
        assert key in structured, key
        assert key in out or key in structured
    assert out["learning_chain"][0] == "knowledge"
    assert "Profitability" in out["frameworks_applied"]
    assert out["financial_dna"]["summary"]
    assert out["case_studies"]["resemblance"]
    assert out["benchmarking"]["never_self_only"] is True
    assert "accounting" in out["confidence"]
    assert "reasoning" in out["confidence"]

    text = (out.get("executive_opinion") or "").lower()
    for lazy in LAZY:
        assert lazy not in text
    for tok in FORBIDDEN:
        assert tok not in text
    assert "own" in (out.get("primary_question_answer") or "").lower() or "support" in (
        out.get("primary_question_answer") or ""
    ).lower()
    # WHY, not bare number dump
    assert "leverage" in text or "cash" in text or "return" in text


def test_roe_example_quality():
    out = think(company="HDFC Bank", evidence=_evidence(roe="18"), ticker="HDFCBANK")
    eo = out["executive_opinion"].lower()
    assert "return on equity" in eo or "returns" in eo
    assert "leverage" in eo
    assert not re.search(r"\broe increased to 18%?\b", eo)


def test_incomplete_assessment():
    out = think(
        company="Thin Co",
        evidence={
            "company": "Thin Co",
            "revenue": "",
            "cash_flow": "",
            "debt": "",
            "capital_allocation": "",
            "financial_quality": "",
            "trend": "",
            "narrative": "",
            "evidence_refs": [],
        },
        confidence={"evidence": 0.2, "knowledge": 0.2, "freshness": 0.2},
    )
    assert out["quality_checks"]["incomplete"] is True
    assert "Incomplete Financial Assessment" in (out["executive_opinion"] or "")


def test_analyse_soft_wire_and_domain_guard():
    op = analyse(
        {
            "ticker": "HDFCBANK",
            "company_analysis": {
                "company_name": "HDFC Bank",
                "financial_intelligence": {
                    "narrative": "Earnings quality supported by NIMs and fee income.",
                    "trend": "Improving cash conversion",
                    "roe": "16%",
                    "cash_flow": "Operating cash conversion improving",
                    "capital_allocation": "Disciplined reinvestment",
                    "financial_quality": "Strong",
                    "confidence": 0.7,
                    "what_deserves_monitoring": ["Liability costs"],
                },
            },
            "company_dossier": {"financial_statements": {"roe": "16%", "leverage": "Conservative"}},
            "data_validation": {"confidence": 0.68, "checks": ["Statements validated"], "freshness": 0.7},
            "sector_intelligence": {"peers": ["Private bank peers"], "global_peers": ["Global bank peers"]},
        }
    )
    assert op.get("iai_financial_v1") is True
    assert op["role"] == "financial"
    assert op["executive_opinion"]
    assert isinstance(op["financial_dna"], dict)
    blob = " ".join(
        [
            op.get("summary") or "",
            op.get("executive_opinion") or "",
            " ".join(op.get("strengths") or []),
        ]
    ).lower()
    for tok in ("moat", "brand", "pricing power", "p/e", "intrinsic"):
        assert tok not in blob


def test_package_consumes_financial_opinion():
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
            "valuation_intelligence": {"pe": 18.5, "margin_of_safety": "Modest", "confidence": 0.62},
        },
        company_dossier={"identity": {"company_name": "HDFC Bank"}},
        data_validation={"confidence": 0.68, "checks": ["Statements validated"]},
    )
    fin = (pack.get("analyst_opinions") or {}).get("financial") or {}
    assert fin.get("summary") or fin.get("executive_opinion")
    assert fin.get("iai_financial_v1") is True
