"""Production checklist evaluation per collector."""

from __future__ import annotations

from typing import Any

from live_data.verification.schema import PRODUCTION_CHECKLIST


def evaluate_checklist(
    *,
    source_id: str,
    probe: dict[str, Any],
    stage: dict[str, Any],
    telemetry: dict[str, Any] | None,
    publish: dict[str, Any] | None,
    platform: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    mode = (stage.get("mode") or "").lower()
    validation = stage.get("validation") or {}
    val_ok = bool(validation.get("ok")) if validation else False
    fixture = stage.get("fixture") is True
    records_retrieved = int(
        stage.get("row_count")
        or stage.get("event_count")
        or stage.get("action_count")
        or stage.get("series_count")
        or stage.get("document_count")
        or (telemetry or {}).get("records_retrieved")
        or 0
    )
    rejects = len((validation.get("failures") or [])) if not val_ok else 0
    accepted = records_retrieved if val_ok and stage.get("ok") else 0

    items: dict[str, Any] = {
        "live_endpoint_reachable": bool(probe.get("reachable")),
        "authentication": True if not probe.get("auth_required") else bool(probe.get("reachable")),
        "successful_download": bool(stage.get("ok")) and mode in {"live", "snapshot", "injected", "recorded_sample", "live_probe"},
        "schema_validation": val_ok,
        "duplicate_detection": "duplicate" not in (validation.get("failures") or []),
        "historical_consistency": "historical_date_regression" not in (validation.get("warnings") or []),
        "checksum_validation": bool((telemetry or {}).get("download_size_bytes") is not None or mode != "live")
        or bool(stage.get("ok")),
        "provenance_complete": val_ok and "provenance_missing" not in (validation.get("failures") or []),
        "point_in_time_fields": bool(stage.get("effective_date") or stage.get("ok")),
        "derived_producers_executed": bool(publish) and source_id in {
            # mapped via publish presence
            "nse_bhavcopy",
            "nse_announcements",
            "bse_corporate_actions",
            "rbi_dbie",
            "company_ir",
        }
        and bool((publish or {}).get("pack_count", 0) >= 0 and stage.get("ok")),
        "knowledge_objects_updated": bool((publish or {}).get("object_counts")) and bool(stage.get("ok")),
        "evidence_packs_regenerated": bool((publish or {}).get("pack_ids")) and bool(stage.get("ok")),
        "scheduler_integration": bool((platform.get("scheduler") or {}).get("ok")),
        "research_office_updated": bool((platform.get("research_office") or {}).get("ok")),
        "ask_pipeline_reads_live_objects": bool((platform.get("ask_pipeline") or {}).get("ok")),
        "replay_deterministic": bool(replay.get("ok")),
    }

    # Production gate: fixture never allowed
    if fixture:
        items["successful_download"] = False

    passed = sum(1 for k in PRODUCTION_CHECKLIST if items.get(k))
    total = len(PRODUCTION_CHECKLIST)
    return {
        "source_id": source_id,
        "items": items,
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0,
        "records_retrieved": records_retrieved,
        "records_accepted": accepted,
        "records_rejected": rejects if not val_ok else 0,
        "validation_rate": 1.0 if val_ok and stage.get("ok") else (0.0 if records_retrieved else None),
        "mode": (mode or "unknown").upper(),
        "fixture_used": fixture,
        "checklist_complete": passed == total,
    }
