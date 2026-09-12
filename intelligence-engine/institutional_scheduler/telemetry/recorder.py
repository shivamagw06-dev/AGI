"""Scheduler telemetry recorder."""

from __future__ import annotations

from typing import Any

from institutional_scheduler import store
from institutional_scheduler.schema import SCHEDULER_VERSION


def record_run_telemetry(run: dict[str, Any]) -> dict[str, Any]:
    results = run.get("workflow_results") or {}
    retries = sum(int((r or {}).get("retries") or 0) for r in results.values())
    skipped = [wid for wid, r in results.items() if (r or {}).get("status") == "skipped"]
    errors = [
        {"workflow": wid, "error": (r or {}).get("error")}
        for wid, r in results.items()
        if (r or {}).get("status") == "error"
    ]
    row = {
        "run_id": run.get("run_id"),
        "date": run.get("date"),
        "version": SCHEDULER_VERSION,
        "duration_ms": run.get("duration_ms"),
        "latency_ms": run.get("duration_ms"),
        "retries": retries,
        "skipped_tasks": skipped,
        "errors": errors,
        "warnings": store.list_alerts(limit=20),
        "coverage": ((results.get("coverage_validation") or {}).get("payload")),
        "health": run.get("health"),
        "state": run.get("state"),
        "workflows": list(results.keys()),
        "fabricated": False,
    }
    store.append_telemetry(row)
    return row
