"""Company Analysis Engine production facade — soft adapters only."""

from __future__ import annotations

from typing import Any

from company_analysis.assemble import analyse_company
from company_analysis.flags import flags_dict, is_enabled
from company_analysis.schema import COMPANY_ANALYSIS_VERSION, PROGRAMME, PROGRAMME_SHORT
from company_analysis import store as ca_store


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": COMPANY_ANALYSIS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "not_an_engine": True,
        "not_a_recommendation_engine": True,
        "not_an_llm": True,
        "not_context_assembly": True,
        "flags": flags_dict(),
        "enabled": is_enabled(),
    }


def analyse(
    query: str = "",
    *,
    ticker: str | None = None,
    cid: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
    dvc_pkg: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    irp_pkg: dict[str, Any] | None = None,
    forecast_learning: dict[str, Any] | None = None,
    market_events: dict[str, Any] | None = None,
    record: bool = True,
) -> dict[str, Any]:
    return analyse_company(
        query=query,
        ticker=ticker,
        cid=cid,
        finance_academy=finance_academy,
        sif_pkg=sif_pkg,
        leo_pkg=leo_pkg,
        dvc_pkg=dvc_pkg,
        valuation_pack=valuation_pack,
        irp_pkg=irp_pkg,
        forecast_learning=forecast_learning,
        market_events=market_events,
        record=record,
    )


def package_for_ask_agi(
    query: str,
    *,
    ticker: str | None = None,
    cid: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sif_pkg: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
    dvc_pkg: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    forecast_learning: dict[str, Any] | None = None,
    market_events: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ask AGI soft entry — full company analysis package before IRP."""
    report = analyse(
        query,
        ticker=ticker,
        cid=cid,
        finance_academy=finance_academy,
        sif_pkg=sif_pkg,
        leo_pkg=leo_pkg,
        dvc_pkg=dvc_pkg,
        valuation_pack=valuation_pack,
        forecast_learning=forecast_learning,
        market_events=market_events,
        record=True,
    )
    if not report.get("enabled"):
        return report

    hints = []
    fin_n = ((report.get("financial_intelligence") or {}).get("narrative") or "").strip()
    if fin_n:
        hints.append(fin_n[:280])
    val_n = ((report.get("valuation_intelligence") or {}).get("narrative") or "").strip()
    if val_n:
        hints.append(val_n[:280])
    for c in ((report.get("academy_application") or {}).get("applied_concepts") or [])[:3]:
        if c.get("application"):
            hints.append(str(c["application"])[:240])
    if report.get("investment_thesis"):
        hints.append(str(report["investment_thesis"])[:240])
    readiness = report.get("recommendation_readiness") or {}
    hints.append(f"Recommendation readiness {readiness.get('overall')}% — {readiness.get('gate')}")

    return {
        **report,
        "ask_agi_hints": hints[:10],
        "answer_policy": "institutional_company_analysis_before_isolated_concepts",
    }


def dashboard() -> dict[str, Any]:
    m = ca_store.metrics()
    latest = ca_store.list_reports(limit=10)
    return {
        "programme": PROGRAMME,
        "version": COMPANY_ANALYSIS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "metrics": m,
        "latest_reports": [
            {
                "ticker": r.get("ticker"),
                "generated_at": r.get("generated_at"),
                "business_quality_score": (r.get("business_quality") or {}).get("business_quality_score"),
                "overall_readiness": (r.get("recommendation_readiness") or {}).get("overall"),
                "gate": (r.get("recommendation_readiness") or {}).get("gate"),
                "applied_concepts": len((r.get("academy_application") or {}).get("applied_concepts") or []),
            }
            for r in latest
        ],
        "coverage_dimensions": [
            "analysis",
            "business_quality",
            "financial_quality",
            "sector_quality",
            "knowledge_quality",
            "evidence_quality",
            "recommendation_readiness",
        ],
    }


def quality_gates() -> dict[str, Any]:
    # Deterministic self-check on HDFC-style application
    report = analyse(
        "Should I invest in HDFC Bank?",
        ticker="HDFCBANK",
        sif_pkg={
            "sector_id": "banks",
            "sector_name": "Banks",
            "priority_metrics": ["nim", "casa", "credit_cost", "gnpa", "roe", "cet1"],
        },
        finance_academy={
            "concepts": [
                {"concept_id": "seed_c_roe", "title": "ROE", "definition": "Return on equity", "academy": "accounting"},
                {"concept_id": "seed_c_nim", "title": "Net Interest Margin", "definition": "Bank spread", "academy": "sector_banking"},
                {"concept_id": "seed_c_mos", "title": "Margin of Safety", "definition": "Price vs value", "academy": "investment"},
                {"concept_id": "seed_c_moat", "title": "Economic Moat", "definition": "Durable advantage", "academy": "investment"},
            ]
        },
        cid={
            "ticker": "HDFCBANK",
            "identity": {
                "company_name": "HDFC Bank",
                "sector_id": "banks",
                "sector": "Banks",
            },
            "financials": {"roe": 16.5, "nim": 3.5},
            "valuation": {"pe": 18.0, "historical_pe": 20.0, "pb": 2.5},
            "validated_fields": {"roe": 16.5, "pe": 18.0},
        },
        dvc_pkg={"quality": "high", "validated_fields": {"roe": 16.5, "pe": 18.0}},
        record=False,
    )
    apps = (report.get("academy_application") or {}).get("applied_concepts") or []
    roe_app = next((a for a in apps if "roe" in str(a.get("title") or "").lower()), None)
    applied_ok = bool(roe_app and "casa" in str(roe_app.get("application") or "").lower())
    has_cases = bool(report.get("bull_case") and report.get("bear_case") and report.get("base_case"))
    has_score = (report.get("business_quality") or {}).get("business_quality_score") is not None
    readiness = report.get("recommendation_readiness") or {}
    criteria = {
        "academy_concepts_applied_to_company": applied_ok,
        "sector_specific_reasoning": bool((report.get("sector_intelligence") or {}).get("reasoning")),
        "financial_intelligence_integrated": bool((report.get("financial_intelligence") or {}).get("enabled")),
        "valuation_intelligence_integrated": bool((report.get("valuation_intelligence") or {}).get("enabled")),
        "business_quality_score_generated": has_score,
        "investment_thesis_generated": bool(report.get("investment_thesis")),
        "bull_base_bear_generated": has_cases,
        "historical_evolution_present": bool(report.get("historical_evolution")),
        "evidence_backed": ((report.get("evidence") or {}).get("count") or 0) >= 3,
        "recommendation_gate_not_auto_buy": readiness.get("not_a_recommendation_engine") is True,
        "hdfc_sample_ok": report.get("ticker") == "HDFCBANK",
    }
    passed = all(criteria.values())
    return {
        "programme": PROGRAMME,
        "version": COMPANY_ANALYSIS_VERSION,
        "passed": passed,
        "criteria": criteria,
        "hdfc_readiness": readiness,
        "message": "Company Analysis quality gates passed" if passed else "Company Analysis incomplete",
    }


def production_dashboard() -> dict[str, Any]:
    return dashboard()


def reset_for_tests() -> None:
    ca_store.reset_for_tests()
