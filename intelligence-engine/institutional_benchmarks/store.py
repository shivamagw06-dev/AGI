"""Process-local IBS metrics for Mission Control dashboard."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional


_LOCK = Lock()
_RESULTS: list[dict[str, Any]] = []
_SUITES: list[dict[str, Any]] = []
_PREV_AVG: Optional[float] = None
_METRICS: dict[str, Any] = {
    "runs": 0,
    "passes": 0,
    "fails": 0,
    "suite_runs": 0,
    "hallucinations": 0,
    "broken_provenance": 0,
    "unsupported_conclusions": 0,
    "consistency_failures": 0,
    "score_sum": 0.0,
    "processing_ms_sum": 0.0,
    "sectors": {},
}
_LIMIT = 200


def record(result: dict[str, Any]) -> None:
    with _LOCK:
        _RESULTS.append(
            {
                "case_id": result.get("case_id"),
                "sector": result.get("sector"),
                "passed": result.get("passed"),
                "score": result.get("research_quality_score"),
                "failure_codes": list(result.get("failure_codes") or []),
                "processing_ms": result.get("processing_ms"),
                "quality": {
                    "hallucination_count": (result.get("quality") or {}).get("hallucination_count"),
                    "broken_provenance_count": (result.get("quality") or {}).get("broken_provenance_count"),
                    "unsupported_count": (result.get("quality") or {}).get("unsupported_count"),
                },
                "confidence": ((result.get("confidence_summary") or {}).get("confidence")),
            }
        )
        if len(_RESULTS) > _LIMIT:
            del _RESULTS[: len(_RESULTS) - _LIMIT]
        _METRICS["runs"] = int(_METRICS["runs"]) + 1
        if result.get("passed"):
            _METRICS["passes"] = int(_METRICS["passes"]) + 1
        else:
            _METRICS["fails"] = int(_METRICS["fails"]) + 1
        _METRICS["score_sum"] = float(_METRICS["score_sum"]) + float(result.get("research_quality_score") or 0.0)
        _METRICS["processing_ms_sum"] = float(_METRICS["processing_ms_sum"]) + float(
            result.get("processing_ms") or 0.0
        )
        q = result.get("quality") or {}
        _METRICS["hallucinations"] = int(_METRICS["hallucinations"]) + int(q.get("hallucination_count") or 0)
        _METRICS["broken_provenance"] = int(_METRICS["broken_provenance"]) + int(
            q.get("broken_provenance_count") or 0
        )
        _METRICS["unsupported_conclusions"] = int(_METRICS["unsupported_conclusions"]) + int(
            q.get("unsupported_count") or 0
        )
        if "CONSISTENCY_FAILURE" in (result.get("failure_codes") or []):
            _METRICS["consistency_failures"] = int(_METRICS["consistency_failures"]) + 1
        sec = str(result.get("sector") or "UNKNOWN")
        sectors = _METRICS["sectors"]
        if not isinstance(sectors, dict):
            sectors = {}
            _METRICS["sectors"] = sectors
        row = sectors.setdefault(sec, {"runs": 0, "passes": 0, "score_sum": 0.0})
        row["runs"] = int(row["runs"]) + 1
        if result.get("passed"):
            row["passes"] = int(row["passes"]) + 1
        row["score_sum"] = float(row["score_sum"]) + float(result.get("research_quality_score") or 0.0)


def record_suite(suite: dict[str, Any]) -> None:
    global _PREV_AVG
    with _LOCK:
        avg = suite.get("average_score")
        regression = None
        if _PREV_AVG is not None and isinstance(avg, (int, float)):
            regression = round(float(avg) - float(_PREV_AVG), 2)
        if isinstance(avg, (int, float)):
            _PREV_AVG = float(avg)
        _SUITES.append({**deepcopy(suite), "regression_since_previous": regression})
        if len(_SUITES) > 20:
            del _SUITES[: len(_SUITES) - 20]
        _METRICS["suite_runs"] = int(_METRICS["suite_runs"]) + 1


def latest_suite() -> Optional[dict[str, Any]]:
    with _LOCK:
        return deepcopy(_SUITES[-1]) if _SUITES else None


def metrics() -> dict[str, Any]:
    with _LOCK:
        m = deepcopy(_METRICS)
        results = list(_RESULTS)
        prev = _PREV_AVG
        latest = deepcopy(_SUITES[-1]) if _SUITES else None
    runs = int(m.get("runs") or 0)
    avg_score = round(float(m.get("score_sum") or 0.0) / runs, 2) if runs else 0.0
    avg_ms = round(float(m.get("processing_ms_sum") or 0.0) / runs, 2) if runs else 0.0
    confs = [r.get("confidence") for r in results if isinstance(r.get("confidence"), (int, float))]
    avg_conf = round(sum(confs) / len(confs), 3) if confs else None
    sector_cov = {
        k: {
            "runs": v.get("runs"),
            "passes": v.get("passes"),
            "average_score": round(float(v.get("score_sum") or 0.0) / max(1, int(v.get("runs") or 0)), 2),
        }
        for k, v in (m.get("sectors") or {}).items()
    }
    return {
        **m,
        "average_score": avg_score,
        "average_processing_ms": avg_ms,
        "average_confidence": avg_conf,
        "sector_coverage": sector_cov,
        "regression_since_previous_release": (latest or {}).get("regression_since_previous"),
        "previous_average": prev,
        "panels": {
            "benchmarks_passed": m.get("passes"),
            "benchmarks_failed": m.get("fails"),
            "average_score": avg_score,
            "sector_coverage": len(sector_cov),
            "hallucination_count": m.get("hallucinations"),
            "broken_provenance": m.get("broken_provenance"),
            "unsupported_conclusions": m.get("unsupported_conclusions"),
            "consistency_failures": m.get("consistency_failures"),
            "average_confidence": avg_conf,
            "average_processing_ms": avg_ms,
            "regression_since_previous": (latest or {}).get("regression_since_previous"),
        },
    }


def reset_for_tests() -> None:
    global _RESULTS, _SUITES, _PREV_AVG
    with _LOCK:
        _RESULTS = []
        _SUITES = []
        _PREV_AVG = None
        for k in list(_METRICS.keys()):
            if k == "sectors":
                _METRICS[k] = {}
            elif k in {"score_sum", "processing_ms_sum"}:
                _METRICS[k] = 0.0
            else:
                _METRICS[k] = 0
