"""Institutional Operations Dashboard."""

from __future__ import annotations

from typing import Any

from institutional_scheduler import store
from institutional_scheduler.dag.morning import build_morning_dag
from institutional_scheduler.health.engine import health_snapshot
from institutional_scheduler.schema import PROGRAMME, SCHEDULER_VERSION
from institutional_scheduler.workflows.definitions import list_workflows


def operations_dashboard() -> dict[str, Any]:
    status = store.get_status()
    history = store.list_history(limit=10)
    today = store.utc_now()[:10]
    todays = [h for h in history if h.get("date") == today]
    latest = history[0] if history else None
    health = health_snapshot(latest)
    reports = store.get_reports(latest.get("run_id") if latest else None)
    return {
        "programme": PROGRAMME,
        "version": SCHEDULER_VERSION,
        "north_star": "morning_system_ready",
        "todays_run": todays[0] if todays else latest,
        "scheduler_status": status.get("state"),
        "current_stage": status.get("current_workflow"),
        "workflow_progress": {
            "completed": (latest or {}).get("completed"),
            "failures": (latest or {}).get("failures"),
        },
        "coverage": (latest or {}).get("coverage"),
        "evidence_quality": ((latest or {}).get("quality_gates") if latest else None)
        or (((latest or {}).get("workflow_results") or {}).get("quality_gates")),
        "validation": (((latest or {}).get("workflow_results") or {}).get("quality_gates")),
        "reports": list(reports.keys()) if reports else (latest or {}).get("reports_generated"),
        "ready_status": {
            "state": status.get("state"),
            "system_ready": status.get("system_ready"),
        },
        "historical_performance": {
            "runs": len(history),
            "workflow_stats": store.workflow_stats(),
            "recent_durations_ms": [h.get("duration_ms") for h in history[:10]],
        },
        "health": health,
        "dag": build_morning_dag(),
        "workflows": [{"workflow_id": w["workflow_id"], "level": w["level"]} for w in list_workflows()],
        "mission_control_ops": {
            "current_workflow": status.get("current_workflow"),
            "running_tasks": [status.get("current_workflow")] if status.get("state") == "RUNNING" else [],
            "completed_tasks": list(((latest or {}).get("completed") or {}).keys()),
            "failures": (latest or {}).get("failures") or [],
            "retries": sum(
                int((r or {}).get("retries") or 0)
                for r in ((latest or {}).get("workflow_results") or {}).values()
            ),
            "warnings": store.list_alerts(limit=10),
            "eta": None,
            "system_ready": status.get("system_ready"),
        },
        "fabricated": False,
    }
