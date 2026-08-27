"""Collector telemetry store — run-level operational metrics."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from live_data import store

_TELEMETRY: list[dict[str, Any]] = []
_MAX = 500


def reset_telemetry() -> None:
    _TELEMETRY.clear()


def new_run_id() -> str:
    return f"lidi_verify_{uuid.uuid4().hex[:12]}"


def record_telemetry(row: dict[str, Any]) -> dict[str, Any]:
    rec = {
        "collector_id": row.get("collector_id"),
        "source_id": row.get("source_id"),
        "version": row.get("version"),
        "run_id": row.get("run_id") or new_run_id(),
        "execution_time_ms": row.get("execution_time_ms"),
        "download_size_bytes": row.get("download_size_bytes"),
        "validation_count": row.get("validation_count", 0),
        "reject_count": row.get("reject_count", 0),
        "retry_count": row.get("retry_count", 0),
        "timeouts": row.get("timeouts", 0),
        "failures": row.get("failures") or [],
        "warnings": row.get("warnings") or [],
        "snapshot_used": bool(row.get("snapshot_used")),
        "freshness": row.get("freshness"),
        "mode": row.get("mode"),
        "records_retrieved": row.get("records_retrieved", 0),
        "records_accepted": row.get("records_accepted", 0),
        "records_rejected": row.get("records_rejected", 0),
        "at": store.utc_now(),
        "fabricated": False,
        "fixture": False,
    }
    _TELEMETRY.append(rec)
    _TELEMETRY[:] = _TELEMETRY[-_MAX:]
    store.put_report(f"telemetry_{rec['run_id']}_{rec.get('source_id') or 'x'}", rec)
    return deepcopy(rec)


def list_telemetry(*, limit: int = 100, source_id: str | None = None) -> list[dict[str, Any]]:
    rows = list(reversed(_TELEMETRY))
    if source_id:
        rows = [r for r in rows if r.get("source_id") == source_id]
    return deepcopy(rows[: max(1, limit)])


def latest_telemetry(source_id: str) -> dict[str, Any] | None:
    for r in reversed(_TELEMETRY):
        if r.get("source_id") == source_id:
            return deepcopy(r)
    return None
