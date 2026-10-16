"""In-process IHG telemetry store."""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

_LOCK = Lock()
_RUNS: deque[dict[str, Any]] = deque(maxlen=200)
_TELEMETRY: dict[str, Any] = {
    "n_runs": 0,
    "n_hypotheses": 0,
    "n_rejected": 0,
    "n_contested": 0,
    "n_insufficient": 0,
    "sum_confidence": 0.0,
    "sum_hypotheses_per_run": 0,
}


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.appendleft(dict(summary))
        _TELEMETRY["n_runs"] = int(_TELEMETRY["n_runs"]) + 1
        _TELEMETRY["n_hypotheses"] = int(_TELEMETRY["n_hypotheses"]) + int(summary.get("n_hypotheses") or 0)
        _TELEMETRY["n_rejected"] = int(_TELEMETRY["n_rejected"]) + int(summary.get("n_rejected") or 0)
        _TELEMETRY["n_contested"] = int(_TELEMETRY["n_contested"]) + int(summary.get("n_contested") or 0)
        if summary.get("insufficient_evidence"):
            _TELEMETRY["n_insufficient"] = int(_TELEMETRY["n_insufficient"]) + 1
        _TELEMETRY["sum_confidence"] = float(_TELEMETRY["sum_confidence"]) + float(
            summary.get("average_confidence") or 0.0
        )
        _TELEMETRY["sum_hypotheses_per_run"] = int(_TELEMETRY["sum_hypotheses_per_run"]) + int(
            summary.get("n_hypotheses") or 0
        )


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RUNS)[: max(1, min(limit, 200))]]


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        n = int(_TELEMETRY["n_runs"])
        avg_conf = (float(_TELEMETRY["sum_confidence"]) / n) if n else 0.0
        avg_n = (float(_TELEMETRY["sum_hypotheses_per_run"]) / n) if n else 0.0
        return {
            "n_runs": n,
            "n_hypotheses": int(_TELEMETRY["n_hypotheses"]),
            "n_rejected": int(_TELEMETRY["n_rejected"]),
            "n_contested": int(_TELEMETRY["n_contested"]),
            "n_insufficient": int(_TELEMETRY["n_insufficient"]),
            "average_hypotheses": round(avg_n, 2),
            "average_confidence": round(avg_conf, 3),
        }
