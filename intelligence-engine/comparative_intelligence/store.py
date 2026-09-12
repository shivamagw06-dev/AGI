"""Process-local CIO-01 metrics."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any


_LOCK = Lock()
_METRICS: dict[str, Any] = {
    "comparisons_served": 0,
    "companies_compared_total": 0,
    "modules_invoked_total": 0,
    "assembly_ms_sum": 0.0,
    "assembly_ms_count": 0,
    "evidence_refs_total": 0,
    "comparison_types": {},
    "last_tickers": None,
    "last_mean_confidence": None,
}


def record_icr(icr: dict[str, Any]) -> None:
    with _LOCK:
        _METRICS["comparisons_served"] = int(_METRICS["comparisons_served"]) + 1
        tickers = list(icr.get("tickers") or [])
        _METRICS["companies_compared_total"] = int(_METRICS["companies_compared_total"]) + len(tickers)
        mods = list(icr.get("modules_invoked") or [])
        _METRICS["modules_invoked_total"] = int(_METRICS["modules_invoked_total"]) + len(mods) * max(len(tickers), 1)
        ms = float(icr.get("assembly_ms") or 0.0)
        _METRICS["assembly_ms_sum"] = float(_METRICS["assembly_ms_sum"]) + ms
        _METRICS["assembly_ms_count"] = int(_METRICS["assembly_ms_count"]) + 1
        refs = icr.get("evidence_references") or []
        _METRICS["evidence_refs_total"] = int(_METRICS["evidence_refs_total"]) + len(refs)
        ctype = str(icr.get("comparison_type") or "unknown")
        by = _METRICS["comparison_types"]
        if not isinstance(by, dict):
            by = {}
            _METRICS["comparison_types"] = by
        by[ctype] = int(by.get(ctype) or 0) + 1
        _METRICS["last_tickers"] = tickers
        conf = icr.get("confidence") if isinstance(icr.get("confidence"), dict) else {}
        _METRICS["last_mean_confidence"] = conf.get("mean_confidence")


def metrics() -> dict[str, Any]:
    with _LOCK:
        m = deepcopy(_METRICS)
    count = int(m.get("assembly_ms_count") or 0)
    avg = (float(m.get("assembly_ms_sum") or 0.0) / count) if count else 0.0
    served = int(m.get("comparisons_served") or 0)
    return {
        **m,
        "average_assembly_time_ms": round(avg, 3),
        "avg_companies_per_comparison": round(
            float(m.get("companies_compared_total") or 0) / served, 3
        )
        if served
        else 0.0,
        "panels": {
            "comparisons_served": m.get("comparisons_served"),
            "companies_compared": m.get("companies_compared_total"),
            "modules_invoked": m.get("modules_invoked_total"),
            "average_assembly_time": round(avg, 3),
            "evidence_reuse": int(m.get("evidence_refs_total") or 0),
            "coverage": m.get("comparison_types") or {},
            "confidence": {"last_mean_confidence": m.get("last_mean_confidence")},
        },
    }


def reset_for_tests() -> None:
    with _LOCK:
        _METRICS["comparisons_served"] = 0
        _METRICS["companies_compared_total"] = 0
        _METRICS["modules_invoked_total"] = 0
        _METRICS["assembly_ms_sum"] = 0.0
        _METRICS["assembly_ms_count"] = 0
        _METRICS["evidence_refs_total"] = 0
        _METRICS["comparison_types"] = {}
        _METRICS["last_tickers"] = None
        _METRICS["last_mean_confidence"] = None
