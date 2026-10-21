"""Health engine — running/queued/completed/failed/skipped/retrying/blocked."""

from __future__ import annotations

from typing import Any

from institutional_scheduler import store
from institutional_scheduler.schema import SCHEDULER_VERSION


def health_snapshot(run: dict[str, Any] | None = None) -> dict[str, Any]:
    status = store.get_status()
    stats = store.workflow_stats()
    run = run or store.get_run(status.get("current_run_id") or "") or {}
    results = (run.get("workflow_results") or {}) if run else {}
    counts = {
        "running": 1 if status.get("state") == "RUNNING" else 0,
        "queued": 0,
        "completed": sum(1 for r in results.values() if (r or {}).get("status") in {"ok", "degraded", "partial", "skipped"}),
        "failed": sum(1 for r in results.values() if (r or {}).get("status") == "error"),
        "skipped": sum(1 for r in results.values() if (r or {}).get("status") == "skipped"),
        "retrying": 0,
        "blocked": 1 if status.get("state") == "MAINTENANCE" else 0,
    }
    avg = None
    durs = [s.get("average_runtime_ms") for s in stats.values() if s.get("average_runtime_ms") is not None]
    if durs:
        avg = round(sum(durs) / len(durs), 2)
    return {
        "version": SCHEDULER_VERSION,
        "state": status.get("state"),
        "system_ready": status.get("system_ready"),
        "current_workflow": status.get("current_workflow"),
        "current_run_id": status.get("current_run_id"),
        "counts": counts,
        "average_runtime_ms": avg,
        "workflow_stats": stats,
        "failure_rate": _overall_failure_rate(stats),
        "alerts": store.list_alerts(limit=20),
        "fabricated": False,
    }


def _overall_failure_rate(stats: dict[str, Any]) -> float | None:
    runs = sum(int(s.get("runs") or 0) for s in stats.values())
    fails = sum(int(s.get("failures") or 0) for s in stats.values())
    if not runs:
        return None
    return round(fails / runs, 4)
