"""Immutable-ish execution history + live status store."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

_STATUS: dict[str, Any] = {
    "state": "INITIALISING",
    "current_run_id": None,
    "current_workflow": None,
    "system_ready": False,
    "maintenance": False,
}
_HISTORY: list[dict[str, Any]] = []
_TELEMETRY: list[dict[str, Any]] = []
_REPORTS: dict[str, dict[str, Any]] = {}
_WORKFLOW_STATS: dict[str, dict[str, Any]] = {}
_ALERTS: list[dict[str, Any]] = []


def reset() -> None:
    _STATUS.clear()
    _STATUS.update(
        {
            "state": "INITIALISING",
            "current_run_id": None,
            "current_workflow": None,
            "system_ready": False,
            "maintenance": False,
        }
    )
    _HISTORY.clear()
    _TELEMETRY.clear()
    _REPORTS.clear()
    _WORKFLOW_STATS.clear()
    _ALERTS.clear()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def set_status(**kwargs: Any) -> dict[str, Any]:
    _STATUS.update(kwargs)
    return deepcopy(_STATUS)


def get_status() -> dict[str, Any]:
    return deepcopy(_STATUS)


def append_history(row: dict[str, Any]) -> None:
    # Immutable append — never mutate prior rows
    _HISTORY.append(deepcopy(row))


def list_history(*, limit: int = 50) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_HISTORY[-max(1, limit) :])))


def get_run(run_id: str) -> dict[str, Any] | None:
    for row in reversed(_HISTORY):
        if row.get("run_id") == run_id:
            return deepcopy(row)
    return None


def append_telemetry(row: dict[str, Any]) -> None:
    _TELEMETRY.append(deepcopy(row))


def list_telemetry(*, limit: int = 100) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_TELEMETRY[-max(1, limit) :])))


def put_reports(run_id: str, reports: dict[str, Any]) -> None:
    _REPORTS[run_id] = deepcopy(reports)


def get_reports(run_id: str | None = None) -> dict[str, Any]:
    if run_id:
        return deepcopy(_REPORTS.get(run_id) or {})
    if not _REPORTS:
        return {}
    latest = list(_REPORTS.keys())[-1]
    return deepcopy(_REPORTS[latest])


def note_workflow_stat(workflow_id: str, *, ok: bool, duration_ms: int) -> None:
    st = _WORKFLOW_STATS.setdefault(
        workflow_id,
        {"runs": 0, "successes": 0, "failures": 0, "durations_ms": []},
    )
    st["runs"] += 1
    if ok:
        st["successes"] += 1
    else:
        st["failures"] += 1
    st["durations_ms"] = (st["durations_ms"] + [duration_ms])[-50:]


def workflow_stats() -> dict[str, Any]:
    out = {}
    for wid, st in _WORKFLOW_STATS.items():
        durs = st.get("durations_ms") or []
        runs = st.get("runs") or 0
        out[wid] = {
            "runs": runs,
            "successes": st.get("successes"),
            "failures": st.get("failures"),
            "success_rate": round((st.get("successes") or 0) / runs, 4) if runs else None,
            "average_runtime_ms": round(sum(durs) / len(durs), 2) if durs else None,
            "historical_runtime_ms": list(durs[-10:]),
            "failure_rate": round((st.get("failures") or 0) / runs, 4) if runs else None,
        }
    return deepcopy(out)


def alert(level: str, message: str, *, workflow_id: str | None = None) -> None:
    _ALERTS.append(
        {
            "level": level,
            "message": message,
            "workflow_id": workflow_id,
            "at": utc_now(),
        }
    )


def list_alerts(*, limit: int = 50) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_ALERTS[-max(1, limit) :])))
