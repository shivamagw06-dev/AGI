"""Process-local IO desk cache + IO-01 IRP metrics."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any


_LOCK = Lock()
_DESK: dict[str, Any] | None = None

# IO-01 orchestration metrics (additive; never used for analysis)
_IRP_METRICS: dict[str, Any] = {
    "requests_served": 0,
    "modules_invoked_total": 0,
    "assembly_ms_sum": 0.0,
    "assembly_ms_count": 0,
    "evidence_refs_total": 0,
    "packages_by_type": {},
    "modules_by_id": {},
    "last_ticker": None,
    "last_package_type": None,
    "last_mean_confidence": None,
}


def put_desk(desk: dict[str, Any]) -> dict[str, Any]:
    global _DESK
    with _LOCK:
        _DESK = deepcopy(desk)
    return desk


def get_desk() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_DESK) if _DESK else None


def record_irp(irp: dict[str, Any]) -> None:
    """Record orchestration telemetry from an assembled IRP."""
    with _LOCK:
        _IRP_METRICS["requests_served"] = int(_IRP_METRICS["requests_served"]) + 1
        mods = list(irp.get("modules_invoked") or [])
        _IRP_METRICS["modules_invoked_total"] = int(_IRP_METRICS["modules_invoked_total"]) + len(mods)
        ms = float(irp.get("assembly_ms") or 0.0)
        _IRP_METRICS["assembly_ms_sum"] = float(_IRP_METRICS["assembly_ms_sum"]) + ms
        _IRP_METRICS["assembly_ms_count"] = int(_IRP_METRICS["assembly_ms_count"]) + 1
        refs = irp.get("evidence_references") or []
        _IRP_METRICS["evidence_refs_total"] = int(_IRP_METRICS["evidence_refs_total"]) + len(refs)
        pkg = str(irp.get("package_type") or "unknown")
        by_pkg = _IRP_METRICS["packages_by_type"]
        if not isinstance(by_pkg, dict):
            by_pkg = {}
            _IRP_METRICS["packages_by_type"] = by_pkg
        by_pkg[pkg] = int(by_pkg.get(pkg) or 0) + 1
        by_mod = _IRP_METRICS["modules_by_id"]
        if not isinstance(by_mod, dict):
            by_mod = {}
            _IRP_METRICS["modules_by_id"] = by_mod
        for m in mods:
            by_mod[str(m)] = int(by_mod.get(str(m)) or 0) + 1
        _IRP_METRICS["last_ticker"] = irp.get("ticker")
        _IRP_METRICS["last_package_type"] = pkg
        conf = irp.get("confidence") if isinstance(irp.get("confidence"), dict) else {}
        _IRP_METRICS["last_mean_confidence"] = conf.get("mean_confidence")


def irp_metrics() -> dict[str, Any]:
    with _LOCK:
        m = deepcopy(_IRP_METRICS)
    count = int(m.get("assembly_ms_count") or 0)
    avg = (float(m.get("assembly_ms_sum") or 0.0) / count) if count else 0.0
    served = int(m.get("requests_served") or 0)
    refs = int(m.get("evidence_refs_total") or 0)
    return {
        **m,
        "average_assembly_time_ms": round(avg, 3),
        "evidence_reuse": {
            "total_references": refs,
            "avg_references_per_request": round(refs / served, 3) if served else 0.0,
        },
        "coverage": {
            "packages_by_type": m.get("packages_by_type") or {},
            "modules_by_id": m.get("modules_by_id") or {},
        },
        "confidence": {
            "last_mean_confidence": m.get("last_mean_confidence"),
        },
    }


def reset_for_tests() -> None:
    global _DESK
    with _LOCK:
        _DESK = None
        _IRP_METRICS["requests_served"] = 0
        _IRP_METRICS["modules_invoked_total"] = 0
        _IRP_METRICS["assembly_ms_sum"] = 0.0
        _IRP_METRICS["assembly_ms_count"] = 0
        _IRP_METRICS["evidence_refs_total"] = 0
        _IRP_METRICS["packages_by_type"] = {}
        _IRP_METRICS["modules_by_id"] = {}
        _IRP_METRICS["last_ticker"] = None
        _IRP_METRICS["last_package_type"] = None
        _IRP_METRICS["last_mean_confidence"] = None
