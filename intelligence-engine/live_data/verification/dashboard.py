"""Collector Health Dashboard — Track 2 operational board."""

from __future__ import annotations

from typing import Any

from live_data import store
from live_data.verification.certify import get_certification, summary as cert_summary
from live_data.verification.schema import COLLECTOR_SPECS, VERIFY_VERSION
from live_data.verification.telemetry import latest_telemetry, list_telemetry


def collector_health_dashboard() -> dict[str, Any]:
    last = store.get_report("last_verification") or {}
    rows_from_verify = last.get("collectors") or []
    by_sid = {r.get("source_id"): r for r in rows_from_verify}

    columns = [
        "collector",
        "official_source",
        "status",
        "LIVE",
        "SEED",
        "FIXTURE",
        "SNAPSHOT",
        "last_successful_run",
        "records_retrieved",
        "records_accepted",
        "records_rejected",
        "validation_rate",
        "knowledge_objects_updated",
        "evidence_packs_updated",
        "replay_status",
        "freshness",
        "latency",
        "scheduler_status",
        "mission_control_status",
    ]

    rows = []
    for spec in COLLECTOR_SPECS:
        sid = spec["source_id"]
        v = by_sid.get(sid) or {}
        cert = get_certification(sid)
        tel = latest_telemetry(sid) or {}
        mode = v.get("mode") or "UNKNOWN"
        rows.append(
            {
                "collector": spec["name"],
                "official_source": spec["official_source"],
                "status": v.get("status") or cert.get("level") or "DEVELOPMENT",
                "LIVE": bool(v.get("LIVE")) if v else mode == "LIVE",
                "SEED": bool(v.get("SEED")),
                "FIXTURE": bool(v.get("FIXTURE")),
                "SNAPSHOT": bool(v.get("SNAPSHOT")),
                "last_successful_run": v.get("last_successful_run") or cert.get("last_live_success_at"),
                "records_retrieved": v.get("records_retrieved") if v else tel.get("records_retrieved"),
                "records_accepted": v.get("records_accepted") if v else tel.get("records_accepted"),
                "records_rejected": v.get("records_rejected") if v else tel.get("records_rejected"),
                "validation_rate": v.get("validation_rate"),
                "knowledge_objects_updated": v.get("knowledge_objects_updated"),
                "evidence_packs_updated": v.get("evidence_packs_updated"),
                "replay_status": v.get("replay_status") or "UNKNOWN",
                "freshness": v.get("freshness") or tel.get("freshness"),
                "latency": v.get("latency_ms"),
                "scheduler_status": v.get("scheduler_status"),
                "mission_control_status": v.get("mission_control_status"),
                "source_id": sid,
                "certification_level": cert.get("level"),
                "consecutive_live_successes": cert.get("consecutive_live_successes"),
            }
        )

    return {
        "title": "Collector Health Dashboard",
        "version": VERIFY_VERSION,
        "north_star": "production_certified_live_collectors",
        "columns": columns,
        "rows": rows,
        "certification_summary": cert_summary(),
        "last_verification_run_id": last.get("run_id"),
        "quality_gates": last.get("quality_gates"),
        "telemetry_n": len(list_telemetry(limit=500)),
        "fabricated": False,
    }
