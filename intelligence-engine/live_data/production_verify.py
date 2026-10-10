"""Track 2 production surfaces — verification, certification, health dashboard."""

from __future__ import annotations

from typing import Any

from live_data.verification.certify import get_certification, summary as certification_summary
from live_data.verification.dashboard import collector_health_dashboard
from live_data.verification.probe import probe_endpoints, summarize_probes
from live_data.verification.report import readiness_score, write_certification_report
from live_data.verification.runner import run_production_verification
from live_data.verification.schema import FREEZE_LOCKS, MODULE_CODE, PROGRAMME, VERIFY_VERSION
from live_data.verification.telemetry import list_telemetry
from live_data import store


def verify(**kwargs: Any) -> dict[str, Any]:
    return run_production_verification(**kwargs)


def certification() -> dict[str, Any]:
    return {
        "version": VERIFY_VERSION,
        "summary": certification_summary(),
        "collectors": get_certification(),
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
    }


def health_dashboard() -> dict[str, Any]:
    return collector_health_dashboard()


def telemetry(*, limit: int = 100, source_id: str | None = None) -> dict[str, Any]:
    rows = list_telemetry(limit=limit, source_id=source_id)
    return {"n": len(rows), "telemetry": rows, "fabricated": False}


def probes() -> dict[str, Any]:
    report = probe_endpoints()
    return {**report, "summary": summarize_probes(report)}


def report_status() -> dict[str, Any]:
    last = store.get_report("last_verification") or {}
    written = store.get_report("LIVE_DATA_CERTIFICATION_REPORT") or {}
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": VERIFY_VERSION,
        "last_run_id": last.get("run_id"),
        "last_finished_at": last.get("finished_at"),
        "readiness": readiness_score(last) if last else None,
        "report_path": (written or {}).get("path"),
        "quality_gates": last.get("quality_gates"),
        "fabricated": False,
    }


def generate_report() -> dict[str, Any]:
    last = store.get_report("last_verification")
    if not last:
        last = run_production_verification(morning_dry_run=True)
    return write_certification_report(last)


def status() -> dict[str, Any]:
    last = store.get_report("last_verification") or {}
    cert = certification_summary()
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": VERIFY_VERSION,
        "state": "CERTIFIED"
        if cert.get("all_certified")
        else ("VERIFYING" if last else "IDLE"),
        "certification": cert,
        "last_verification_run_id": last.get("run_id"),
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
    }
