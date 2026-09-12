"""S13 — Ask pipeline telemetry."""

from __future__ import annotations

from typing import Any

from ask_pipeline import store
from ask_pipeline.schema import PIPELINE_VERSION


def build_telemetry(
    *,
    context: dict[str, Any],
    stages: dict[str, Any],
    policy: dict[str, Any],
    gates: dict[str, Any],
    total_ms: int,
) -> dict[str, Any]:
    executed = []
    skipped = []
    errors = []
    for name, stage in stages.items():
        if not isinstance(stage, dict):
            continue
        st = stage.get("status")
        if st == "executed" or st == "degraded":
            executed.append(name)
        elif st == "skipped_by_policy":
            skipped.append(name)
        elif st == "error":
            errors.append({"stage": name, "error": stage.get("error")})

    evidence = stages.get("evidence") or {}
    record = {
        "pipeline_id": context.get("pipeline_id"),
        "replay_id": context.get("replay_id"),
        "pipeline_version": PIPELINE_VERSION,
        "question": context.get("question"),
        "intent": context.get("intent"),
        "started_at": context.get("timestamp"),
        "finished_at": store.utc_now(),
        "latency_ms": total_ms,
        "modules_executed": executed,
        "modules_skipped": skipped,
        "errors": errors,
        "evidence_coverage": evidence.get("coverage"),
        "decision_quality": (stages.get("decision_quality") or {}).get("decision_id"),
        "outcome_registered": (stages.get("outcome") or {}).get("decision_id"),
        "validation": (stages.get("governance") or {}).get("validation"),
        "quality_gates": gates,
        "policy": {
            "run_portfolio": policy.get("run_portfolio"),
            "run_planner": policy.get("run_planner"),
            "run_outcome_registration": policy.get("run_outcome_registration"),
            "run_learning": False,
        },
        "fabricated": False,
    }
    store.put_telemetry(context["pipeline_id"], record)
    return record
