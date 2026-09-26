"""Morning Health — Institutional Company Intelligence Coverage."""

from __future__ import annotations

from typing import Any

from knowledge_factory.company_intelligence import store as ici_store
from knowledge_factory.company_intelligence.schema import ICI_VERSION, INSTITUTIONAL_COMPLETE_LEVEL


def company_intelligence_dashboard(*, ensure: bool = True) -> dict[str, Any]:
    if ensure and ici_store.count() == 0:
        from knowledge_factory.company_intelligence.pipeline import run_company_intelligence_pipeline

        run_company_intelligence_pipeline()

    rows = ici_store.list_all()
    n = len(rows) or 1
    by_level = {i: 0 for i in range(8)}
    bm_ok = mgmt_ok = own_ok = comp_ok = tl_ok = 0
    scores: list[float] = []
    unknown = 0
    val_fail = 0
    ready = 0

    for obj in rows:
        lvl = int(obj.get("coverage_level") or 0)
        by_level[lvl] = by_level.get(lvl, 0) + 1
        mods = obj.get("modules") or {}
        if mods.get("business_model"):
            bm_ok += 1
        if mods.get("management"):
            mgmt_ok += 1
        if mods.get("ownership"):
            own_ok += 1
        if mods.get("competition"):
            comp_ok += 1
        if mods.get("timeline"):
            tl_ok += 1
        scores.append(float(obj.get("intelligence_score") or 0))
        unknown += int(obj.get("unknown_fields") or 0)
        if obj.get("quality", {}).get("failed_gates"):
            val_fail += 1
        if obj.get("institutional_ready") or lvl >= INSTITUTIONAL_COMPLETE_LEVEL:
            ready += 1

    last = ici_store.last_run() or {}
    board = {
        "ici_version": ICI_VERSION,
        "title": "Institutional Company Intelligence — Morning Health",
        "north_star": "institutional_company_intelligence_coverage",
        "layer_label": "Company Intelligence (not Universe Coverage Index)",
        "kpi_rule": "Deepen qualitative company knowledge without changing reasoning.",
        "architecture_frozen": "REASONING_V1",
        "companies": len(rows),
        "institutional_company_coverage": ready,
        "institutional_company_coverage_pct": round(100.0 * ready / n, 2),
        "business_model_coverage_pct": round(100.0 * bm_ok / n, 2),
        "management_coverage_pct": round(100.0 * mgmt_ok / n, 2),
        "ownership_coverage_pct": round(100.0 * own_ok / n, 2),
        "competition_coverage_pct": round(100.0 * comp_ok / n, 2),
        "timeline_coverage_pct": round(100.0 * tl_ok / n, 2),
        "average_intelligence_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "unknown_fields": unknown,
        "validation_failures": val_fail,
        "coverage_levels": by_level,
        "level_7_complete": by_level.get(7, 0),
        "last_pipeline_status": last.get("status"),
        "last_runtime_seconds": last.get("runtime_seconds"),
        "fabricated": False,
    }
    return board


__all__ = ["company_intelligence_dashboard"]
