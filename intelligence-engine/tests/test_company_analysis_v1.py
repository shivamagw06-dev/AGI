"""Company Analysis Engine V1 — apply Academy to companies (not Context Assembly)."""

from __future__ import annotations

from company_analysis.academy_apply import apply_academy
from company_analysis.assemble import analyse_company
from company_analysis.identity import identify_company
from company_analysis.production import health, package_for_ask_agi, quality_gates, reset_for_tests
from company_analysis.schema import COMPANY_ANALYSIS_VERSION


def setup_function() -> None:
    reset_for_tests()


def test_health_and_naming():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == COMPANY_ANALYSIS_VERSION
    assert h["not_context_assembly"] is True
    assert h["not_a_recommendation_engine"] is True
    assert h["flags"]["COMPANY_ANALYSIS"] is True


def test_hdfc_roe_applied_with_banking_lenses():
    identity = identify_company(
        "HDFCBANK",
        cid={"ticker": "HDFCBANK", "identity": {"sector_id": "banks", "sector": "Banks", "company_name": "HDFC Bank"}},
        sif_pkg={"sector_id": "banks", "sector_name": "Banks"},
    )
    assert identity["ticker"] == "HDFCBANK"
    assert identity["peers"]
    applied = apply_academy(
        identity=identity,
        finance_academy={
            "concepts": [
                {"concept_id": "c1", "title": "ROE", "definition": "Return on equity", "academy": "accounting"},
                {"concept_id": "c2", "title": "Margin of Safety", "definition": "Price vs value", "academy": "investment"},
            ]
        },
    )
    roe = next(c for c in applied["applied_concepts"] if c["title"] == "ROE")
    text = (roe.get("application") or "").lower()
    assert "casa" in text
    assert "credit cost" in text or "credit" in text
    assert "capital" in text


def test_nestle_roe_applied_with_fmcg_lenses():
    identity = identify_company(
        "NESTLEIND",
        cid={"ticker": "NESTLEIND", "identity": {"sector_id": "fmcg", "sector": "FMCG"}},
    )
    applied = apply_academy(
        identity=identity,
        finance_academy={
            "concepts": [{"concept_id": "c1", "title": "ROE", "definition": "Return on equity", "academy": "accounting"}]
        },
    )
    roe = next(c for c in applied["applied_concepts"] if c["title"] == "ROE")
    text = (roe.get("application") or "").lower()
    assert "brand" in text or "roic" in text
    assert "pricing" in text or "cash conversion" in text or "working capital" in text


def test_full_hdfc_report_and_ask_agi_package():
    report = analyse_company(
        query="Should I invest in HDFC Bank?",
        ticker="HDFCBANK",
        sif_pkg={
            "sector_id": "banks",
            "sector_name": "Banks",
            "priority_metrics": ["nim", "casa", "credit_cost", "gnpa", "roe"],
        },
        finance_academy={
            "concepts": [
                {"concept_id": "seed_c_roe", "title": "ROE", "academy": "accounting"},
                {"concept_id": "seed_c_nim", "title": "Net Interest Margin", "academy": "sector_banking"},
                {"concept_id": "seed_c_moat", "title": "Economic Moat", "academy": "investment"},
            ]
        },
        cid={
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank", "sector_id": "banks", "sector": "Banks"},
            "financials": {"roe": 16.5, "nim": 3.4, "loan_growth": 0.12},
            "valuation": {"pe": 18.0, "historical_pe": 20.0, "pb": 2.6},
            "validated_fields": {"roe": 16.5, "pe": 18.0},
        },
        dvc_pkg={"quality": "high", "validated_fields": {"roe": 16.5, "pe": 18.0}},
        record=True,
    )
    assert report["enabled"] is True
    assert report["ticker"] == "HDFCBANK"
    assert report["bull_case"] and report["bear_case"] and report["base_case"]
    assert (report.get("business_quality") or {}).get("business_quality_score") is not None
    assert (report.get("evidence") or {}).get("count", 0) >= 3
    readiness = report.get("recommendation_readiness") or {}
    assert readiness.get("not_a_recommendation_engine") is True
    assert readiness.get("gate") in {"Eligible", "Recommendation Withheld"}

    pkg = package_for_ask_agi("HDFC Bank analysis", ticker="HDFCBANK")
    assert pkg.get("ask_agi_hints")
    assert "institutional_company_analysis" in (pkg.get("answer_policy") or "")


def test_quality_gates_pass():
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["criteria"]["academy_concepts_applied_to_company"] is True
    assert gates["criteria"]["recommendation_gate_not_auto_buy"] is True
