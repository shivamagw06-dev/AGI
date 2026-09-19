"""In-process ICR telemetry store."""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

_LOCK = Lock()
_RUNS: deque[dict[str, Any]] = deque(maxlen=200)
_TELEMETRY: dict[str, Any] = {
    "n_runs": 0,
    "n_cases": 0,
    "n_bull": 0,
    "n_base": 0,
    "n_bear": 0,
    "sum_confidence": 0.0,
    "sum_disagreements": 0,
    "sum_missing": 0,
}


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.appendleft(dict(summary))
        _TELEMETRY["n_runs"] = int(_TELEMETRY["n_runs"]) + 1
        _TELEMETRY["n_cases"] = int(_TELEMETRY["n_cases"]) + int(summary.get("n_cases") or 0)
        for role in ("bull", "base", "bear"):
            if summary.get(f"has_{role}"):
                _TELEMETRY[f"n_{role}"] = int(_TELEMETRY[f"n_{role}"]) + 1
        _TELEMETRY["sum_confidence"] = float(_TELEMETRY["sum_confidence"]) + float(
            summary.get("confidence") or 0
        )
        _TELEMETRY["sum_disagreements"] = int(_TELEMETRY["sum_disagreements"]) + int(
            summary.get("n_disagreements") or 0
        )
        _TELEMETRY["sum_missing"] = int(_TELEMETRY["sum_missing"]) + int(summary.get("n_missing") or 0)


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RUNS)[: max(1, min(limit, 200))]]


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        n = max(1, int(_TELEMETRY["n_runs"]))
        return {
            "n_runs": int(_TELEMETRY["n_runs"]),
            "n_cases": int(_TELEMETRY["n_cases"]),
            "n_bull": int(_TELEMETRY["n_bull"]),
            "n_base": int(_TELEMETRY["n_base"]),
            "n_bear": int(_TELEMETRY["n_bear"]),
            "average_confidence": round(float(_TELEMETRY["sum_confidence"]) / n, 3),
            "unresolved_disagreements": int(_TELEMETRY["sum_disagreements"]),
            "missing_evidence": int(_TELEMETRY["sum_missing"]),
        }
