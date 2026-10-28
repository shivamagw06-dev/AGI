"""IIVI pipeline — soft KF only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.industry_intelligence import store as iivi_store
from knowledge_factory.industry_intelligence.dashboards import industry_dashboard
from knowledge_factory.industry_intelligence.objects.compile import compile_all_industries
from knowledge_factory.industry_intelligence.schema import IIVI_VERSION

PIPELINE_VERSION = "iivi-pipeline-v2.0.0"


def run_industry_intelligence_pipeline() -> dict[str, Any]:
    t0 = time.perf_counter()
    pack = compile_all_industries(persist=True)
    dash = industry_dashboard(ensure=False)
    runtime = round(time.perf_counter() - t0, 2)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "iivi_version": IIVI_VERSION,
        "industries": pack.get("industries"),
        "companies_mapped": pack.get("companies_mapped"),
        "company_map_complete": pack.get("company_map_complete"),
        "institutional_ready": pack.get("institutional_ready"),
        "institutional_ready_pct": pack.get("institutional_ready_pct"),
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if pack.get("company_map_complete") and pack.get("institutional_ready_pct") == 100.0 else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
        "future_economic_network_graph": "declared_later_sprint",
    }
    iivi_store.record_run(report)
    return report
