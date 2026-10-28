"""In-process IEW telemetry store (process-local, fail-open)."""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

_LOCK = Lock()
_RUNS: deque[dict[str, Any]] = deque(maxlen=200)
_TELEMETRY: dict[str, Any] = {
    "n_runs": 0,
    "n_evidence_scored": 0,
    "n_excluded": 0,
    "n_conflicts": 0,
    "sum_weight": 0.0,
    "source_counts": {},
}


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.appendleft(dict(summary))
        _TELEMETRY["n_runs"] = int(_TELEMETRY["n_runs"]) + 1
        _TELEMETRY["n_evidence_scored"] = int(_TELEMETRY["n_evidence_scored"]) + int(
            summary.get("n_weighted") or 0
        )
        _TELEMETRY["n_excluded"] = int(_TELEMETRY["n_excluded"]) + int(summary.get("n_excluded") or 0)
        _TELEMETRY["n_conflicts"] = int(_TELEMETRY["n_conflicts"]) + int(summary.get("n_conflicts") or 0)
        _TELEMETRY["sum_weight"] = float(_TELEMETRY["sum_weight"]) + float(summary.get("sum_weight") or 0)
        for src, n in (summary.get("source_counts") or {}).items():
            sc = _TELEMETRY["source_counts"]
            assert isinstance(sc, dict)
            sc[str(src)] = int(sc.get(str(src)) or 0) + int(n)


def latest_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(x) for x in list(_RUNS)[: max(1, min(limit, 200))]]


def telemetry_snapshot() -> dict[str, Any]:
    with _LOCK:
        n = int(_TELEMETRY["n_runs"])
        scored = int(_TELEMETRY["n_evidence_scored"])
        avg = (float(_TELEMETRY["sum_weight"]) / scored) if scored else 0.0
        sources = dict(_TELEMETRY["source_counts"] or {})
        dominant = sorted(sources.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        return {
            "n_runs": n,
            "n_evidence_scored": scored,
            "n_excluded": int(_TELEMETRY["n_excluded"]),
            "n_conflicts": int(_TELEMETRY["n_conflicts"]),
            "average_weight": round(avg, 2),
            "dominant_sources": [{"source": s, "count": c} for s, c in dominant],
            "source_counts": sources,
        }
