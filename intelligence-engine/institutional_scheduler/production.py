"""Institutional Scheduler production facade."""

from __future__ import annotations

from typing import Any

from institutional_scheduler import store
from institutional_scheduler.dashboards.operations import operations_dashboard
from institutional_scheduler.health.engine import health_snapshot
from institutional_scheduler.scheduler.engine import get_scheduler
from institutional_scheduler.schema import FREEZE_LOCKS, PROGRAMME, SCHEDULER_VERSION
from institutional_scheduler.workflows.definitions import list_workflows


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": SCHEDULER_VERSION,
        "soft_wire_only": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/scheduler",
        "no_reasoning": True,
        "no_intelligence": True,
        **health_snapshot(),
    }


def dashboard() -> dict[str, Any]:
    return operations_dashboard()


def status() -> dict[str, Any]:
    return get_scheduler().status()


def run_morning(**kwargs: Any) -> dict[str, Any]:
    return get_scheduler().run_morning(**kwargs)


def history(*, limit: int = 50) -> dict[str, Any]:
    rows = store.list_history(limit=limit)
    return {"n": len(rows), "runs": rows, "fabricated": False}


def workflows() -> dict[str, Any]:
    return {"n": len(list_workflows()), "workflows": list_workflows(), "fabricated": False}


def retry(workflow_id: str, **kwargs: Any) -> dict[str, Any]:
    return get_scheduler().retry_workflow(workflow_id, **kwargs)


def reports(run_id: str | None = None) -> dict[str, Any]:
    return {"run_id": run_id, "reports": store.get_reports(run_id), "fabricated": False}


def telemetry(*, limit: int = 100) -> dict[str, Any]:
    rows = store.list_telemetry(limit=limit)
    return {"n": len(rows), "items": rows, "fabricated": False}
