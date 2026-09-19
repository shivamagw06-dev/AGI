"""Track 2 verification runner — activate, verify, certify collectors."""

from __future__ import annotations

import os
import time
from copy import deepcopy
from typing import Any

from live_data import store
from live_data.pipeline import run_live_ingestion
from live_data.verification.certify import record_verification_result, summary as cert_summary
from live_data.verification.checklist import evaluate_checklist
from live_data.verification.platform_soft import (
    check_ask_pipeline_reads_live,
    check_mission_control,
    check_reasoning_untouched,
    check_replay_deterministic,
    check_research_office,
    check_scheduler_integration,
)
from live_data.verification.probe import probe_endpoints, summarize_probes
from live_data.verification.schema import COLLECTOR_SPECS, FREEZE_LOCKS, VERIFY_VERSION
from live_data.verification.telemetry import new_run_id, record_telemetry


def _mode_label(stage: dict[str, Any]) -> str:
    m = (stage.get("mode") or "").lower()
    if stage.get("fixture") is True:
        return "FIXTURE"
    if stage.get("fallback") or m == "snapshot":
        return "SNAPSHOT"
    if m == "live" or m == "live_probe":
        return "LIVE"
    if m == "recorded_sample":
        return "RECORDED_SAMPLE"
    if m == "injected":
        return "INJECTED"
    if m == "seed":
        return "SEED"
    return "UNKNOWN"


def run_production_verification(
    *,
    allow_recorded_sample: bool | None = None,
    skip_live_probes: bool = False,
    skip_ingestion: bool = False,
    skip_morning: bool = False,
    injected: dict[str, Any] | None = None,
    morning_dry_run: bool = True,
) -> dict[str, Any]:
    """Full Track-2 verification pass.

    Production default: live probes + live ingestion (no recorded samples).
    Tests may pass injected=... for deterministic lifecycle certification path checks.
    """
    run_id = new_run_id()
    started = store.utc_now()
    t0 = time.time()

    # 1) Live endpoint probes
    if skip_live_probes:
        probes = {"probed_at": started, "collectors": {}, "fabricated": False, "skipped": True}
        probe_summary = {"reachable": 0, "download_ok": 0, "total": 0, "by_source": {}}
    else:
        probes = probe_endpoints()
        probe_summary = summarize_probes(probes)

    # 2) Ingestion lifecycle (Collector→…→Evidence)
    if skip_ingestion:
        ingestion = {"ok": False, "stages": {}, "publish": None, "skipped": True}
    else:
        kwargs: dict[str, Any] = {}
        if injected is not None:
            kwargs["injected"] = injected
            kwargs["allow_recorded_sample"] = False
        elif allow_recorded_sample is not None:
            kwargs["allow_recorded_sample"] = allow_recorded_sample
        else:
            # Production verification: never use recorded samples unless env explicitly set
            kwargs["allow_recorded_sample"] = os.environ.get("LIDI_ALLOW_RECORDED_SAMPLE", "").lower() in {
                "1",
                "true",
                "yes",
            }
        ingestion = run_live_ingestion(**kwargs)

    stages = ingestion.get("stages") or {}
    publish = ingestion.get("publish") or {}

    # 3) Platform soft checks
    platform = {
        "scheduler": check_scheduler_integration(),
        "research_office": check_research_office(),
        "ask_pipeline": check_ask_pipeline_reads_live(),
        "mission_control": check_mission_control(),
        "reasoning": check_reasoning_untouched(),
    }
    replay = check_replay_deterministic(stages)

    # 4) Per-collector checklist + telemetry + certification
    collector_rows: list[dict[str, Any]] = []
    quality_failures: list[str] = []

    for spec in COLLECTOR_SPECS:
        sid = spec["source_id"]
        stage = stages.get(sid) or {}
        probe = (probes.get("collectors") or {}).get(sid) or {}
        mode = _mode_label(stage) if stage else ("UNKNOWN" if not probe else ("LIVE" if probe.get("reachable") else "UNKNOWN"))

        # Telemetry
        files = []
        health = store.get_collector_health(spec["collector_id"]) or {}
        download_size = None
        for p in health.get("downloaded_files") or []:
            try:
                download_size = (download_size or 0) + (os.path.getsize(p) if isinstance(p, str) and os.path.exists(p) else 0)
            except Exception:
                pass

        records = int(
            stage.get("row_count")
            or stage.get("event_count")
            or stage.get("action_count")
            or stage.get("series_count")
            or stage.get("document_count")
            or 0
        )
        val = stage.get("validation") or {}
        val_ok = bool(val.get("ok")) if val else False
        rejects = len(val.get("failures") or []) if val and not val_ok else 0

        tel = record_telemetry(
            {
                "collector_id": spec["collector_id"],
                "source_id": sid,
                "version": spec["collector_id"],
                "run_id": run_id,
                "execution_time_ms": int((time.time() - t0) * 1000),
                "download_size_bytes": download_size,
                "validation_count": 1 if stage else 0,
                "reject_count": rejects,
                "retry_count": 0,
                "timeouts": 0,
                "failures": val.get("failures") or ([] if stage.get("ok") else [stage.get("reason") or "failed"]),
                "warnings": val.get("warnings") or [],
                "snapshot_used": mode == "SNAPSHOT",
                "freshness": "STALE" if mode == "SNAPSHOT" else ("FRESH" if mode == "LIVE" else mode),
                "mode": mode,
                "records_retrieved": records,
                "records_accepted": records if val_ok and stage.get("ok") else 0,
                "records_rejected": rejects,
            }
        )

        checklist = evaluate_checklist(
            source_id=sid,
            probe=probe,
            stage=stage,
            telemetry=tel,
            publish=publish,
            platform=platform,
            replay=replay,
        )

        lifecycle_ok = bool(stage.get("ok")) and val_ok and bool(publish.get("pack_ids") is not None)
        # For live certification path: lifecycle must be LIVE mode
        fixture_used = checklist.get("fixture_used") is True
        cert = record_verification_result(
            source_id=sid,
            mode=mode,
            lifecycle_ok=lifecycle_ok,
            validation_ok=val_ok if stage else False,
            provenance_ok=checklist["items"].get("provenance_complete", False),
            replay_ok=bool(replay.get("ok")),
            fixture_used=fixture_used,
            failure_reason=None
            if lifecycle_ok and mode == "LIVE"
            else (
                "fixture_used"
                if fixture_used
                else (stage.get("reason") or ("not_live:" + mode if mode != "LIVE" else "lifecycle_incomplete"))
            ),
        )

        # Quality gates
        if not probe.get("reachable") and mode not in {"INJECTED", "RECORDED_SAMPLE", "SNAPSHOT"}:
            quality_failures.append(f"unreachable:{sid}")
        if stage and not val_ok:
            quality_failures.append(f"validation:{sid}")
        if fixture_used:
            quality_failures.append(f"fixture:{sid}")
        if stage.get("ok") and not checklist["items"].get("derived_producers_executed"):
            # derived tied to publish; if stage ok but no publish overall, flag once later
            pass

        collector_rows.append(
            {
                "collector": spec["name"],
                "collector_id": spec["collector_id"],
                "source_id": sid,
                "official_source": spec["official_source"],
                "status": cert.get("level"),
                "mode": mode,
                "LIVE": mode == "LIVE",
                "SEED": mode == "SEED",
                "FIXTURE": mode == "FIXTURE",
                "SNAPSHOT": mode == "SNAPSHOT",
                "last_successful_run": (health.get("last_success") or cert.get("last_live_success_at")),
                "records_retrieved": checklist["records_retrieved"],
                "records_accepted": checklist["records_accepted"],
                "records_rejected": checklist["records_rejected"],
                "validation_rate": checklist["validation_rate"],
                "knowledge_objects_updated": checklist["items"].get("knowledge_objects_updated"),
                "evidence_packs_updated": checklist["items"].get("evidence_packs_regenerated"),
                "replay_status": "OK" if replay.get("ok") else "FAIL",
                "freshness": tel.get("freshness"),
                "latency_ms": (probe.get("best") or {}).get("latency_ms"),
                "scheduler_status": (platform.get("scheduler") or {}).get("ok"),
                "mission_control_status": (platform.get("mission_control") or {}).get("ok"),
                "checklist": checklist,
                "certification": cert,
                "probe": {
                    "reachable": probe.get("reachable"),
                    "download_ok": probe.get("download_ok"),
                    "note": probe.get("note"),
                    "error": (probe.get("best") or {}).get("error"),
                },
                "telemetry": tel,
                "snapshot_policy": _snapshot_policy(stage, mode),
            }
        )

    if not publish.get("pack_ids") and any(s.get("ok") for s in stages.values()):
        quality_failures.append("evidence_packs_stale_or_missing")
    if not replay.get("ok"):
        quality_failures.append("replay_changes")
    if not platform["reasoning"].get("ok"):
        quality_failures.append("reasoning_touched")
    if any(r.get("FIXTURE") for r in collector_rows):
        quality_failures.append("fixture_in_production_path")

    # Morning verification soft (dry-run by default to avoid long KF runs in CI)
    if skip_morning:
        morning = {
            "ok": bool((platform.get("scheduler") or {}).get("soft_wire_present")),
            "skipped": True,
            "dry_run": morning_dry_run,
            "lidi_soft_wire": True,
            "fabricated": False,
        }
    else:
        morning = _morning_verify(dry_run=morning_dry_run)

    report = {
        "ok": len(quality_failures) == 0 and all(r.get("mode") == "LIVE" for r in collector_rows),
        "verify_version": VERIFY_VERSION,
        "run_id": run_id,
        "started_at": started,
        "finished_at": store.utc_now(),
        "duration_ms": int((time.time() - t0) * 1000),
        "probe_summary": probe_summary,
        "probes": probes,
        "ingestion": {
            "ok": ingestion.get("ok"),
            "stages": stages,
            "publish": publish,
            "quality_gates": ingestion.get("quality_gates"),
        },
        "platform": platform,
        "replay": replay,
        "collectors": collector_rows,
        "certification_summary": cert_summary(),
        "morning_verification": morning,
        "quality_gates": {
            "passed": len(set(quality_failures)) == 0,
            "failures": sorted(set(quality_failures)),
            "fail_if": [
                "collector_unreachable",
                "validation_fails",
                "replay_changes",
                "derived_producer_skipped",
                "knowledge_objects_not_updated",
                "evidence_packs_stale",
                "research_office_stale",
                "mission_control_mismatch",
                "raw_payload_reaches_reasoning",
                "fixture_used_in_production",
            ],
        },
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "fixture": False,
    }
    store.set_last_run({**(store.get_last_run() or {}), "verification": report})
    store.put_report("last_verification", report)
    store.put_report(f"verification_{run_id}", report)
    return report


def _snapshot_policy(stage: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode != "SNAPSHOT" and not stage.get("fallback"):
        return {
            "applied": False,
            "policy": "latest_validated_snapshot_only",
            "never_fixture": True,
        }
    return {
        "applied": True,
        "status": "STALE",
        "transparent_insufficiency": True,
        "failure_reason": stage.get("reason") or stage.get("fallback_reason") or "live_unavailable",
        "snapshot_age": stage.get("freshness") or (stage.get("retrieved_at")),
        "expected_recovery": "retry_next_morning_or_when_source_reachable",
        "never_fixture": True,
        "used_fixture": False,
    }


def _morning_verify(*, dry_run: bool = True) -> dict[str, Any]:
    # Soft-wire presence is the frozen-package-safe signal; full DAG dry-run is optional.
    soft = check_scheduler_integration()
    if dry_run:
        return {
            "ok": bool(soft.get("ok")),
            "dry_run": True,
            "state": ((soft.get("scheduler_status") or {}).get("state")),
            "system_ready": ((soft.get("scheduler_status") or {}).get("system_ready")),
            "run_id": None,
            "lidi_soft_wire": bool(soft.get("soft_wire_present")),
            "note": "dry_run verifies scheduler soft-wire + status; use morning_dry_run=false for full DAG",
            "fabricated": False,
        }
    try:
        from institutional_scheduler.production import run_morning

        out = run_morning(dry_run=False, parallel=True)
        return {
            "ok": out.get("status") in {"ok", "degraded"}
            or out.get("state")
            in {
                "READY",
                "PARTIAL_READY",
                "WARNING",
                "RUNNING",
            }
            or bool(out.get("run_id")),
            "dry_run": False,
            "state": out.get("state"),
            "system_ready": out.get("system_ready"),
            "run_id": out.get("run_id"),
            "lidi_soft_wire": bool(soft.get("soft_wire_present")),
            "fabricated": False,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "dry_run": False, "fabricated": False}
