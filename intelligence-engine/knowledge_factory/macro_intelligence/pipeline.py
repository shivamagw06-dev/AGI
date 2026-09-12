"""Nightly Institutional Macro Intelligence pipeline (Knowledge Factory only)."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.dashboard import institutional_macro_intelligence_dashboard
from knowledge_factory.macro_intelligence.links.company import compile_company_links
from knowledge_factory.macro_intelligence.links.portfolio import portfolio_macro_exposure
from knowledge_factory.macro_intelligence.links.sector import compile_sector_links
from knowledge_factory.macro_intelligence.objects.compile import publish_macro_evidence_pack
from knowledge_factory.macro_intelligence.producers.similarity import similar_regimes
from knowledge_factory.macro_intelligence.schema import IMI_VERSION, MACRO_UNIVERSE

PIPELINE_VERSION = "imi-pipeline-v1.0.0"


def run_macro_intelligence_pipeline(*, as_of: str | None = None) -> dict[str, Any]:
    """
    Collect → Validate → Classify → Update objects → Relationships →
    Company/sector/portfolio links → Publish packs → Validation → Dashboard.
    """
    t0 = time.perf_counter()
    validation_failures: list[dict[str, str]] = []

    pack = publish_macro_evidence_pack(as_of=as_of)
    if pack.get("insufficient"):
        validation_failures.append({"stage": "classify", "reason": "regime_classification_insufficient"})

    company = compile_company_links()
    sector = compile_sector_links()
    portfolio = portfolio_macro_exposure()
    analogues = similar_regimes(top_n=5)

    objects = imi_store.list_objects()
    if len(objects) < len(MACRO_UNIVERSE):
        validation_failures.append(
            {"stage": "objects", "reason": f"macro_objects_incomplete:{len(objects)}/{len(MACRO_UNIVERSE)}"}
        )
    if not analogues.get("found"):
        validation_failures.append({"stage": "similarity", "reason": analogues.get("reason") or "no_analogues"})

    dash = institutional_macro_intelligence_dashboard()
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "imi_version": IMI_VERSION,
        "as_of": as_of or pack.get("as_of") or "current",
        "macro_universe": len(MACRO_UNIVERSE),
        "objects_published": len(objects),
        "active_regimes": list(pack.get("active_regimes") or []),
        "primary_regime": pack.get("primary_regime"),
        "decision_matrix_rows": len((pack.get("decision_matrix") or {}).get("matched_rows") or []),
        "company_links": company.get("n", 0),
        "sector_links": sector.get("n", 0),
        "portfolio_link": portfolio.get("portfolio_id"),
        "historical_analogues": len(analogues.get("matches") or []),
        "validation_failures": validation_failures,
        "dashboard": dash,
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "status": "ok" if not validation_failures else "degraded",
        "knowledge_only": True,
        "phases_1_7_untouched": True,
        "does_not_modify_hd_or_isi": True,
    }
    imi_store.put_report("macro_pipeline", report)
    return report
