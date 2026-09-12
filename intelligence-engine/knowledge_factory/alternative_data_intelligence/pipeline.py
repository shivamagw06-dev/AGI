"""IADI pipeline — soft KF only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.alternative_data_intelligence import store as iadi_store
from knowledge_factory.alternative_data_intelligence.dashboards import alternative_data_dashboard
from knowledge_factory.alternative_data_intelligence.producers.compile import compile_alternative_data
from knowledge_factory.alternative_data_intelligence.schema import IADI_VERSION, PHASE_1_DATASETS

PIPELINE_VERSION = "iadi-pipeline-v2.0.0"


def run_alternative_data_pipeline() -> dict[str, Any]:
    t0 = time.perf_counter()
    iadi_store.reset()
    pack = compile_alternative_data(persist=True)
    dash = alternative_data_dashboard(ensure=False)
    runtime = round(time.perf_counter() - t0, 2)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "iadi_version": IADI_VERSION,
        "delivery_phase": "phase_1_high_signal",
        "phase_1_datasets": list(PHASE_1_DATASETS),
        "datasets": pack.get("dataset_count"),
        "observations": pack.get("observation_count"),
        "phase_1_complete": pack.get("phase_1_complete"),
        "institutional_ready": pack.get("institutional_ready"),
        "failed_datasets": pack.get("failed_datasets"),
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if pack.get("institutional_ready") else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
        "planner_changed": False,
        "prediction_engine": False,
        "soft_wire_only": True,
    }
    iadi_store.record_run(report)
    return report
