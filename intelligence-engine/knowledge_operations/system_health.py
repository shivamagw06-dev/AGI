"""System Health Bar — CGL / KIL / ICF / Scheduler / Collectors / Latency."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _soft(fn, default=None):
    try:
        return fn()
    except Exception as exc:
        return default if default is not None else {"error": str(exc)[:160]}


def _status_label(running: Optional[bool], *, fallback: str = "Unknown") -> str:
    if running is True:
        return "Running"
    if running is False:
        return "Stopped"
    return fallback


def build_system_health() -> Dict[str, Any]:
    cgl_h = _soft(
        lambda: __import__(
            "continuous_gather_learn.production", fromlist=["health"]
        ).health()
    )
    cgl_d = _soft(
        lambda: __import__(
            "continuous_gather_learn.production", fromlist=["dashboard"]
        ).dashboard()
    )
    kil = _soft(
        lambda: __import__(
            "institutional_evidence.production", fromlist=["get_kil_status"]
        ).get_kil_status()
    )
    icf = _soft(
        lambda: __import__(
            "institutional_coverage_factory.production", fromlist=["health"]
        ).health()
    )
    icf_sch = _soft(
        lambda: __import__(
            "institutional_coverage_factory.production", fromlist=["scheduler_status"]
        ).scheduler_status()
    )
    from knowledge_operations.flags import is_koc_enabled
    from knowledge_operations.schema import KOC_VERSION

    cgl_enabled = bool((cgl_h or {}).get("enabled")) if isinstance(cgl_h, dict) else False
    bg = (cgl_h or {}).get("background") if isinstance(cgl_h, dict) else None
    latest = (cgl_d or {}).get("latest_run") if isinstance(cgl_d, dict) else None
    cgl_running = bool(cgl_enabled and ((bg or {}).get("ok") or (latest or {}).get("ok")))
    collector_success = (cgl_d or {}).get("collector_success_rate") if isinstance(cgl_d, dict) else None
    repair_queue = None
    ops = (cgl_d or {}).get("ops") if isinstance(cgl_d, dict) else {}
    if isinstance(ops, dict):
        repair_queue = ops.get("repair_queue")
        if isinstance(ops.get("degraded_collectors"), int):
            degraded = ops["degraded_collectors"]
        else:
            degraded = None
    else:
        degraded = None

    kil_ok = bool((kil or {}).get("ok")) if isinstance(kil, dict) else False
    icf_ok = bool((icf or {}).get("ok") and (icf or {}).get("enabled")) if isinstance(icf, dict) else False
    sch_enabled = bool((icf_sch or {}).get("enabled")) if isinstance(icf_sch, dict) else False

    # Soft latency from latest run
    latency_min = None
    if isinstance(latest, dict) and latest.get("latency_ms") is not None:
        try:
            latency_min = round(float(latest["latency_ms"]) / 60000.0, 1)
        except Exception:
            latency_min = None

    return {
        "ok": True,
        "generated_at": _now(),
        "bar": {
            "cgl": {
                "status": _status_label(cgl_running, fallback="Unknown"),
                "enabled": cgl_enabled,
                "slot": (cgl_d or {}).get("current_slot") if isinstance(cgl_d, dict) else None,
                "latest_run_id": (latest or {}).get("run_id") if isinstance(latest, dict) else None,
                "latest_ok": (latest or {}).get("ok") if isinstance(latest, dict) else None,
            },
            "kil": {
                "status": _status_label(kil_ok, fallback="Unknown"),
                "companies_integrated": (kil or {}).get("companies_integrated")
                if isinstance(kil, dict)
                else None,
                "version": (kil or {}).get("version") if isinstance(kil, dict) else None,
            },
            "icf": {
                "status": _status_label(icf_ok, fallback="Unknown"),
                "version": (icf or {}).get("version") if isinstance(icf, dict) else None,
            },
            "scheduler": {
                "status": "READY" if sch_enabled else "OFF",
                "ticks": (icf_sch or {}).get("ticks") if isinstance(icf_sch, dict) else None,
                "icc_entered_today": (icf_sch or {}).get("icc_entered_today")
                if isinstance(icf_sch, dict)
                else None,
            },
            "collector_health_pct": collector_success,
            "knowledge_latency_minutes": latency_min,
            "repair_queue": repair_queue,
            "degraded_collectors": degraded,
            "auto_repair": "Enabled",
            "koc": {
                "status": "Running" if is_koc_enabled() else "Disabled",
                "version": KOC_VERSION,
            },
        },
        "raw": {
            "cgl_covered": (cgl_d or {}).get("covered_companies") if isinstance(cgl_d, dict) else None,
            "cgl_total": (cgl_d or {}).get("total_companies") if isinstance(cgl_d, dict) else None,
            "hard_coverage_pct": (cgl_d or {}).get("hard_coverage_pct")
            if isinstance(cgl_d, dict)
            else None,
        },
    }
