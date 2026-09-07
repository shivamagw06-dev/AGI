"""Institutional Macro Intelligence Coverage dashboard + north-star KPI."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.dna.catalog import all_macro_dna
from knowledge_factory.macro_intelligence.playbooks.catalog import all_regime_playbooks
from knowledge_factory.macro_intelligence.schema import IMI_VERSION, MACRO_UNIVERSE


def institutional_macro_intelligence_coverage() -> dict[str, Any]:
    objects = imi_store.list_objects()
    pack = imi_store.get_pack("current")
    regimes = imi_store.get_regimes() or {}
    company = imi_store.get_links("company") or {}
    sector = imi_store.get_links("sector") or {}
    portfolio = imi_store.get_links("portfolio") or {}
    report = imi_store.get_report("macro_pipeline") or {}
    dna = all_macro_dna()
    pbs = all_regime_playbooks()

    # Count history rows across known series
    history_rows = 0
    for sid in (
        "interest_rates",
        "inflation",
        "oil",
        "usd_inr",
        "gdp",
        "pmi",
        "credit_growth",
        "dxy",
        "yield_curve",
        "liquidity",
    ):
        history_rows += len(imi_store.get_history(sid))

    company_n = int(company.get("n") or len(company.get("links") or {}))
    sector_n = int(sector.get("n") or len(sector.get("links") or {}))
    portfolio_ok = 1.0 if portfolio.get("portfolio_macro_exposure") else 0.0

    macro_object_coverage = len(objects) / max(1, len(MACRO_UNIVERSE))
    dna_coverage = len(dna) / max(1, len(MACRO_UNIVERSE))
    playbook_coverage = min(1.0, len(pbs) / 8.0)
    regime_coverage = 1.0 if regimes.get("active_regimes") else 0.0
    historical_coverage = 1.0 if history_rows >= 50 else history_rows / 50.0
    relationship_coverage = 1.0 if sector_n > 0 else 0.0
    company_coverage = min(1.0, company_n / 10.0)
    sector_coverage = min(1.0, sector_n / 10.0)
    similarity_coverage = 1.0 if pack and pack.get("active_regimes") is not None else 0.0
    decision_matrix_coverage = 1.0 if (pack or {}).get("decision_matrix") else 0.0

    failures = list(report.get("validation_failures") or [])
    evidence_quality = 1.0 if pack and not failures else (0.7 if pack else 0.0)

    components = {
        "macro_objects": round(macro_object_coverage, 4),
        "historical_depth": round(historical_coverage, 4),
        "macro_relationships": round(relationship_coverage, 4),
        "historical_regimes": round(regime_coverage, 4),
        "sector_relationships": round(sector_coverage, 4),
        "company_relationships": round(company_coverage, 4),
        "playbooks": round(playbook_coverage, 4),
        "historical_analogues": round(similarity_coverage, 4),
        "evidence_quality": round(evidence_quality, 4),
        "dna": round(dna_coverage, 4),
        "portfolio": round(portfolio_ok, 4),
        "decision_matrix": round(decision_matrix_coverage, 4),
    }
    coverage = sum(components.values()) / len(components)

    return {
        "north_star_kpi": "institutional_macro_intelligence_coverage",
        "coverage": round(coverage, 4),
        "components": components,
        "counts": {
            "macro_universe": len(MACRO_UNIVERSE),
            "macro_objects": len(objects),
            "dna": len(dna),
            "playbooks": len(pbs),
            "packs": 1 if pack else 0,
            "regimes_active": len(regimes.get("active_regimes") or []),
            "history_rows": history_rows,
            "company_links": company_n,
            "sector_links": sector_n,
            "portfolio_links": 1 if portfolio_ok else 0,
        },
        "macro_intelligence_coverage": round(macro_object_coverage, 4),
        "historical_coverage": round(historical_coverage, 4),
        "regime_coverage": round(regime_coverage, 4),
        "macro_relationship_coverage": round(relationship_coverage, 4),
        "company_coverage": round(company_coverage, 4),
        "sector_coverage": round(sector_coverage, 4),
        "portfolio_coverage": round(portfolio_ok, 4),
        "historical_similarity_coverage": round(similarity_coverage, 4),
        "decision_matrix_coverage": round(decision_matrix_coverage, 4),
        "evidence_quality": round(evidence_quality, 4),
        "validation_failures": failures,
        "imi_version": IMI_VERSION,
        "knowledge_only": True,
        "reasoning_architecture": "frozen_v1",
    }


def institutional_macro_intelligence_dashboard() -> dict[str, Any]:
    kpi = institutional_macro_intelligence_coverage()
    return {
        "dashboard": "institutional_macro_intelligence",
        "kpi": kpi,
        "status": "operational" if float(kpi.get("coverage") or 0) >= 0.7 else "building",
        "imi_version": IMI_VERSION,
    }


# Alias used by production wiring
macro_intelligence_dashboard = institutional_macro_intelligence_dashboard
