"""Institutional Sector Intelligence nightly pipeline — KF only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.sector_intelligence import store as isi_store
from knowledge_factory.sector_intelligence.dashboard import sector_intelligence_dashboard
from knowledge_factory.sector_intelligence.objects.compile import compile_sector_object
from knowledge_factory.sector_intelligence.producers.core import produce_cross_sector_rankings
from knowledge_factory.sector_intelligence.schema import ISI_VERSION, SECTOR_UNIVERSE

PIPELINE_VERSION = "isi-pipeline-v1.0.0"


def run_sector_intelligence_pipeline(sectors: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    sectors = list(sectors or SECTOR_UNIVERSE)
    objects = []
    failures = []
    for s in sectors:
        try:
            obj = compile_sector_object(s)
            objects.append(s)
            if obj.get("insufficient"):
                failures.append({"sector": s, "reason": "insufficient_members_or_history"})
        except Exception as exc:
            failures.append({"sector": s, "reason": str(exc)})

    rankings = produce_cross_sector_rankings(sectors)
    isi_store.put_rankings(rankings)
    dash = sector_intelligence_dashboard(sectors=sectors)
    runtime = round(time.perf_counter() - t0, 2)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "isi_version": ISI_VERSION,
        "sectors": len(sectors),
        "objects_published": len(objects),
        "validation_failures": failures,
        "rankings": {
            "strongest_roic_sector": (rankings.get("strongest_roic_sector") or {}).get("sector"),
        },
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if len(objects) == len(sectors) else "degraded",
    }
    isi_store.put_report("sector_pipeline", report)
    return report
