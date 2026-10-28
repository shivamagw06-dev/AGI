"""In-process ICC telemetry store."""

from __future__ import annotations

from collections import Counter, deque
from threading import Lock
from typing import Any

_LOCK = Lock()
_RUNS: deque[dict[str, Any]] = deque(maxlen=200)
_TELEMETRY: dict[str, Any] = {
    "n_runs": 0,
    "sum_confidence": 0.0,
    "sum_missing_penalty": 0.0,
    "sum_committee_agreement": 0.0,
    "sum_historical": 0.0,
    "sum_framework": 0.0,
    "level_counts": Counter(),
    "uncertainty_drivers": Counter(),
}


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.appendleft(dict(summary))
        _TELEMETRY["n_runs"] = int(_TELEMETRY["n_runs"]) + 1
        _TELEMETRY["sum_confidence"] = float(_TELEMETRY["sum_confidence"]) + float(
            summary.get("overall_confidence") or 0
        )
        _TELEMETRY["sum_missing_penalty"] = float(_TELEMETRY["sum_missing_penalty"]) + float(
            summary.get("missing_evidence_penalty") or 0
        )
        _TELEMETRY["sum_committee_agreement"] = float(_TELEMETRY["sum_committee_agreement"]) + float(
            summary.get("committee_agreement") or 0
        )
        _TELEMETRY["sum_historical"] = float(_TELEMETRY["sum_historical"]) + float(
            summary.get("historical_score") or 0
        )
        _TELEMETRY["sum_framework"] = float(_TELEMETRY["sum_framework"]) + float(
            summary.get("framework_consistency") or 0
        )
        level = str(summary.get("confidence_level") or "unknown")
        _TELEMETRY["level_counts"][level] += 1
        for d in summary.get("uncertainty_drivers") or []:
            _TELEMETRY["uncertainty_drivers"][str(d)] += 1


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RUNS)[: max(1, min(limit, 200))]]


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        n = max(1, int(_TELEMETRY["n_runs"]))
        levels = dict(_TELEMETRY["level_counts"])
        drivers = _TELEMETRY["uncertainty_drivers"].most_common(8)
        return {
            "n_runs": int(_TELEMETRY["n_runs"]),
            "average_confidence": round(float(_TELEMETRY["sum_confidence"]) / n, 2),
            "confidence_distribution": levels,
            "top_uncertainty_drivers": [{"driver": d, "count": c} for d, c in drivers],
            "average_missing_penalty": round(float(_TELEMETRY["sum_missing_penalty"]) / n, 2),
            "average_committee_agreement": round(float(_TELEMETRY["sum_committee_agreement"]) / n, 2),
            "average_historical_score": round(float(_TELEMETRY["sum_historical"]) / n, 2),
            "average_framework_consistency": round(float(_TELEMETRY["sum_framework"]) / n, 2),
        }
