"""In-process IHE telemetry store."""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

_LOCK = Lock()
_RUNS: deque[dict[str, Any]] = deque(maxlen=200)
_TELEMETRY: dict[str, Any] = {
    "n_runs": 0,
    "n_evaluated": 0,
    "n_preferred": 0,
    "n_rejected": 0,
    "n_indeterminate": 0,
    "sum_support": 0.0,
    "sum_conflict": 0.0,
    "sum_confidence": 0.0,
    "sum_missing": 0,
}


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.appendleft(dict(summary))
        _TELEMETRY["n_runs"] = int(_TELEMETRY["n_runs"]) + 1
        _TELEMETRY["n_evaluated"] = int(_TELEMETRY["n_evaluated"]) + int(summary.get("n_evaluated") or 0)
        _TELEMETRY["n_preferred"] = int(_TELEMETRY["n_preferred"]) + int(summary.get("n_preferred") or 0)
        _TELEMETRY["n_rejected"] = int(_TELEMETRY["n_rejected"]) + int(summary.get("n_rejected") or 0)
        _TELEMETRY["n_indeterminate"] = int(_TELEMETRY["n_indeterminate"]) + int(
            summary.get("n_indeterminate") or 0
        )
        _TELEMETRY["sum_support"] = float(_TELEMETRY["sum_support"]) + float(summary.get("average_support") or 0)
        _TELEMETRY["sum_conflict"] = float(_TELEMETRY["sum_conflict"]) + float(
            summary.get("average_conflict_raw") or 0
        )
        _TELEMETRY["sum_confidence"] = float(_TELEMETRY["sum_confidence"]) + float(
            summary.get("average_confidence") or 0
        )
        _TELEMETRY["sum_missing"] = int(_TELEMETRY["sum_missing"]) + int(
            summary.get("missing_evidence_frequency") or 0
        )


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RUNS)[: max(1, min(limit, 200))]]


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        n = int(_TELEMETRY["n_runs"]) or 1
        return {
            "n_runs": int(_TELEMETRY["n_runs"]),
            "n_evaluated": int(_TELEMETRY["n_evaluated"]),
            "n_preferred": int(_TELEMETRY["n_preferred"]),
            "n_rejected": int(_TELEMETRY["n_rejected"]),
            "n_indeterminate": int(_TELEMETRY["n_indeterminate"]),
            "average_support": round(float(_TELEMETRY["sum_support"]) / n, 2),
            "average_conflict": round(float(_TELEMETRY["sum_conflict"]) / n, 2),
            "average_confidence": round(float(_TELEMETRY["sum_confidence"]) / n, 3),
            "missing_evidence_frequency": int(_TELEMETRY["sum_missing"]),
        }
