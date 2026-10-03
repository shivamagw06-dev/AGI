"""IMEI pipeline — soft KF only. Phase-1 public/auditable expectations."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.market_expectations_intelligence import store as imei_store
from knowledge_factory.market_expectations_intelligence.collectors.consensus_licensed import (
    collect_licensed_consensus,
)
from knowledge_factory.market_expectations_intelligence.collectors.phase1 import (
    collect_phase1_expectations,
)
from knowledge_factory.market_expectations_intelligence.dashboards import expectations_dashboard
from knowledge_factory.market_expectations_intelligence.revisions.engine import (
    build_revision_records,
)
from knowledge_factory.market_expectations_intelligence.schema import IMEI_VERSION
from knowledge_factory.market_expectations_intelligence.surprises.engine import compute_surprises
from knowledge_factory.market_expectations_intelligence.validators.gates import (
    validate_expectation,
)

PIPELINE_VERSION = "imei-pipeline-v2.0.0"


def run_market_expectations_pipeline() -> dict[str, Any]:
    t0 = time.perf_counter()
    imei_store.reset()

    phase1 = collect_phase1_expectations()
    phase2 = collect_licensed_consensus()

    ready: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for e in phase1["expectations"]:
        vr = validate_expectation(e)
        e = dict(e)
        e["validation"] = {
            "status": "pass" if vr["gate_pass"] else "fail",
            "gates": vr["gates"],
            "failures": vr["failures"],
        }
        # Always store for transparency; track readiness separately
        imei_store.put_expectation(e)
        if vr["gate_pass"]:
            ready.append(e)
        elif "unknown_expectation" in vr["failures"]:
            unknown.append(e)
        else:
            failed.append({"expectation_id": e.get("expectation_id"), "failures": vr["failures"]})

    for n in phase1["narratives"]:
        imei_store.put_narrative(n)

    revisions = build_revision_records(ready)
    for r in revisions:
        imei_store.put_revision(r)

    surprises = compute_surprises(ready)
    for s in surprises:
        imei_store.put_surprise(s)

    dash = expectations_dashboard(ensure=False)
    runtime = round(time.perf_counter() - t0, 2)

    # Institutional ready = Phase-1 ready set non-empty, no hard failures, surprises computed
    institutional_ready = len(ready) > 0 and len(failed) == 0 and len(surprises) > 0

    report = {
        "pipeline_version": PIPELINE_VERSION,
        "imei_version": IMEI_VERSION,
        "delivery_phase": "phase_1_public_auditable",
        "expectations_ready": len(ready),
        "unknown_expectations": len(unknown),
        "validation_failures": len(failed),
        "failed_samples": failed[:10],
        "revisions": len(revisions),
        "surprises": len(surprises),
        "narratives": len(phase1["narratives"]),
        "phase_2_consensus": {
            "status": phase2.get("status"),
            "licensed_consensus": phase2.get("licensed_consensus"),
            "note": phase2.get("note"),
        },
        "institutional_ready": institutional_ready,
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if institutional_ready else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
        "planner_changed": False,
        "prediction_engine": False,
        "broker_reports_scraped": False,
        "soft_wire_only": True,
    }
    imei_store.record_run(report)
    return report
