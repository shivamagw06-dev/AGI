"""Morning Board — Institutional Industry & Value Chain Intelligence."""

from __future__ import annotations

from typing import Any

from knowledge_factory.industry_intelligence import store as iivi_store
from knowledge_factory.industry_intelligence.playbooks.catalog import DEEP_INDUSTRIES
from knowledge_factory.industry_intelligence.schema import FUTURE_ECONOMIC_NETWORK_GRAPH, IIVI_VERSION


def industry_dashboard(*, ensure: bool = True) -> dict[str, Any]:
    if ensure and iivi_store.industry_count() == 0:
        from knowledge_factory.industry_intelligence.pipeline import run_industry_intelligence_pipeline

        run_industry_intelligence_pipeline()

    rows = iivi_store.list_industries()
    n = len(rows) or 1
    ready = sum(1 for r in rows if r.get("institutional_ready"))
    scores = [float(r.get("intelligence_score") or 0) for r in rows]
    vc_ok = sum(1 for r in rows if (r.get("modules") or {}).get("value_chain"))
    acct_ok = sum(1 for r in rows if (r.get("modules") or {}).get("accounting"))
    val_ok = sum(1 for r in rows if (r.get("modules") or {}).get("valuation"))
    cycle_ok = sum(1 for r in rows if (r.get("modules") or {}).get("cycles"))
    playbooks = sum(1 for r in rows if r.get("industry_id") in DEEP_INDUSTRIES)
    failures = sum(1 for r in rows if (r.get("quality") or {}).get("failed_gates"))
    unknown = sum(1 for r in rows if (r.get("member_count") or 0) == 0)
    cmap = iivi_store.list_company_map()
    last = iivi_store.last_run() or {}

    return {
        "iivi_version": IIVI_VERSION,
        "title": "Institutional Industry & Value Chain Intelligence — Morning Board",
        "north_star": "institutional_industry_value_chain_coverage",
        "kpi_rule": "Teach how industries work — value chains, accounting, valuation — without changing reasoning.",
        "architecture_frozen": "REASONING_V1",
        "industry_coverage": len(rows),
        "industry_intelligence_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "industry_playbooks": playbooks,
        "value_chain_coverage_pct": round(100.0 * vc_ok / n, 2),
        "accounting_playbooks_pct": round(100.0 * acct_ok / n, 2),
        "valuation_playbooks_pct": round(100.0 * val_ok / n, 2),
        "cycle_coverage_pct": round(100.0 * cycle_ok / n, 2),
        "institutional_ready": ready,
        "institutional_ready_pct": round(100.0 * ready / n, 2),
        "companies_mapped": len(cmap),
        "unknown_industries": unknown,
        "validation_failures": failures,
        "future_roadmap": FUTURE_ECONOMIC_NETWORK_GRAPH,
        "last_pipeline_status": last.get("status"),
        "last_runtime_seconds": last.get("runtime_seconds"),
        "fabricated": False,
    }


__all__ = ["industry_dashboard"]
