"""Ask Pipeline Dashboard."""

from __future__ import annotations

from typing import Any

from ask_pipeline import store
from ask_pipeline.schema import PIPELINE_VERSION, PROGRAMME


def ask_pipeline_dashboard() -> dict[str, Any]:
    rows = store.list_executions(limit=200)
    tel = store.list_telemetry(limit=200)
    latencies = [int(r.get("latency_ms") or 0) for r in rows if r.get("latency_ms") is not None]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else None
    complete = sum(1 for r in rows if r.get("institutionally_complete"))
    decisions = sum(1 for r in rows if r.get("decision_id"))
    outcomes = sum(1 for r in rows if r.get("outcome_decision_id"))
    replay_ready = sum(1 for r in rows if r.get("replay_id"))
    skipped: dict[str, int] = {}
    errors = 0
    for t in tel:
        for s in t.get("modules_skipped") or []:
            skipped[s] = skipped.get(s, 0) + 1
        errors += len(t.get("errors") or [])
    coverage_vals = [float(t["evidence_coverage"]) for t in tel if t.get("evidence_coverage") is not None]
    avg_cov = round(sum(coverage_vals) / len(coverage_vals), 4) if coverage_vals else None

    return {
        "programme": PROGRAMME,
        "version": PIPELINE_VERSION,
        "north_star": "ask_pipeline_institutional_completeness",
        "questions_today": store.questions_today(),
        "questions_total": len(rows),
        "average_latency_ms": avg_latency,
        "pipeline_coverage": {
            "institutionally_complete": complete,
            "complete_pct": round(100.0 * complete / len(rows), 2) if rows else None,
        },
        "evidence_coverage_avg": avg_cov,
        "decision_records": decisions,
        "replay_ready": replay_ready,
        "outcome_registered": outcomes,
        "skipped_modules": skipped,
        "errors": errors,
        "recent": [
            {
                "pipeline_id": r.get("pipeline_id"),
                "intent": r.get("intent"),
                "latency_ms": r.get("latency_ms"),
                "institutionally_complete": r.get("institutionally_complete"),
                "decision_id": r.get("decision_id"),
                "outcome_decision_id": r.get("outcome_decision_id"),
            }
            for r in rows[:20]
        ],
        "fabricated": False,
    }
