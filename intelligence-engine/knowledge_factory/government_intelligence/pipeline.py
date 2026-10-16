"""Government Intelligence pipeline — soft KF only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.government_intelligence import store as igri_store
from knowledge_factory.government_intelligence.dashboard import government_dashboard
from knowledge_factory.government_intelligence.objects.compile import compile_government_intelligence
from knowledge_factory.government_intelligence.schema import IGRI_VERSION

PIPELINE_VERSION = "igri-pipeline-v2.0.0"


def run_government_intelligence_pipeline() -> dict[str, Any]:
    t0 = time.perf_counter()
    pack = compile_government_intelligence(persist=True)
    dash = government_dashboard(ensure=False)
    runtime = round(time.perf_counter() - t0, 2)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "igri_version": IGRI_VERSION,
        "bodies": pack.get("registry", {}).get("body_count"),
        "policies": pack.get("policy_count"),
        "domains": pack.get("domains"),
        "coverage_level": pack.get("coverage_level"),
        "institutional_ready": pack.get("institutional_ready"),
        "quality": pack.get("quality"),
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if pack.get("institutional_ready") else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
        "political_opinion": False,
        "policy_forecast": False,
    }
    igri_store.record_run(report)
    return report
