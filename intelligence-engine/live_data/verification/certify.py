"""Certification state machine — honest levels; CERTIFIED needs 7 consecutive LIVE days."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from live_data import store
from live_data.verification.schema import (
    CERTIFICATION_LEVELS,
    CERTIFIED_CONSECUTIVE_LIVE_RUNS,
    COLLECTOR_SPECS,
)

_CERT: dict[str, dict[str, Any]] = {}


def reset_certification() -> None:
    _CERT.clear()


def _default(source_id: str) -> dict[str, Any]:
    spec = next((s for s in COLLECTOR_SPECS if s["source_id"] == source_id), {})
    return {
        "source_id": source_id,
        "collector_id": spec.get("collector_id"),
        "name": spec.get("name"),
        "official_source": spec.get("official_source"),
        "level": "DEVELOPMENT",
        "consecutive_live_successes": 0,
        "consecutive_required": CERTIFIED_CONSECUTIVE_LIVE_RUNS,
        "last_live_success_at": None,
        "last_failure_at": None,
        "last_failure_reason": None,
        "replay_corruption": False,
        "provenance_failures": 0,
        "validation_failures": 0,
        "fixture_fallback_count": 0,
        "history": [],
        "updated_at": None,
    }


def get_certification(source_id: str | None = None) -> dict[str, Any]:
    if source_id:
        row = _CERT.get(source_id) or store.get_report(f"cert_{source_id}") or _default(source_id)
        return deepcopy(row)
    out = {}
    for s in COLLECTOR_SPECS:
        sid = s["source_id"]
        out[sid] = get_certification(sid)
    return out


def _persist(row: dict[str, Any]) -> dict[str, Any]:
    sid = row["source_id"]
    row["updated_at"] = store.utc_now()
    _CERT[sid] = deepcopy(row)
    store.put_report(f"cert_{sid}", row)
    return deepcopy(row)


def _compute_level(row: dict[str, Any], *, mode: str, lifecycle_ok: bool) -> str:
    if row.get("fixture_fallback_count", 0) > 0:
        return "TESTING"
    if row.get("replay_corruption"):
        return "TESTING"
    consec = int(row.get("consecutive_live_successes") or 0)
    if mode == "LIVE" and lifecycle_ok and consec >= CERTIFIED_CONSECUTIVE_LIVE_RUNS:
        return "CERTIFIED"
    if mode == "LIVE" and lifecycle_ok and consec >= 3:
        return "PRODUCTION_READY"
    if mode == "LIVE" and lifecycle_ok:
        return "STAGING"
    if mode in {"SNAPSHOT"} and lifecycle_ok:
        return "TESTING"
    if mode in {"INJECTED", "RECORDED_SAMPLE"}:
        return "TESTING"
    if mode == "FIXTURE":
        return "DEVELOPMENT"
    return "DEVELOPMENT"


def record_verification_result(
    *,
    source_id: str,
    mode: str,
    lifecycle_ok: bool,
    validation_ok: bool,
    provenance_ok: bool,
    replay_ok: bool,
    fixture_used: bool,
    failure_reason: str | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Update certification from a verification run. Never invent CERTIFIED."""
    row = get_certification(source_id)
    hist = list(row.get("history") or [])
    day = (as_of_date or store.utc_now())[:10]
    now = store.utc_now()
    hist.append(
        {
            "date": day,
            "mode": mode,
            "lifecycle_ok": lifecycle_ok,
            "validation_ok": validation_ok,
            "at": now,
        }
    )
    row["history"] = hist[-60:]

    if fixture_used:
        row["fixture_fallback_count"] = int(row.get("fixture_fallback_count") or 0) + 1
        row["consecutive_live_successes"] = 0
        row["last_failure_at"] = now
        row["last_failure_reason"] = failure_reason or "fixture_used"
    elif not validation_ok:
        row["validation_failures"] = int(row.get("validation_failures") or 0) + 1
        row["consecutive_live_successes"] = 0
        row["last_failure_at"] = now
        row["last_failure_reason"] = failure_reason or "validation_failed"
    elif not provenance_ok:
        row["provenance_failures"] = int(row.get("provenance_failures") or 0) + 1
        row["consecutive_live_successes"] = 0
        row["last_failure_at"] = now
        row["last_failure_reason"] = failure_reason or "provenance_failed"
    elif not replay_ok:
        row["replay_corruption"] = True
        row["consecutive_live_successes"] = 0
        row["last_failure_at"] = now
        row["last_failure_reason"] = failure_reason or "replay_corruption"
    elif mode == "LIVE" and lifecycle_ok:
        # Count at most one success per calendar day
        last_live = row.get("last_live_success_at")
        if not last_live or str(last_live)[:10] != day:
            row["consecutive_live_successes"] = int(row.get("consecutive_live_successes") or 0) + 1
        row["last_live_success_at"] = f"{day}T00:00:00Z"
    else:
        # snapshot / injected / failed live — break CERTIFIED streak
        if mode != "LIVE" or not lifecycle_ok:
            row["consecutive_live_successes"] = 0
        if not lifecycle_ok:
            row["last_failure_at"] = now
            row["last_failure_reason"] = failure_reason or "lifecycle_failed"

    row["level"] = _compute_level(row, mode=mode, lifecycle_ok=lifecycle_ok and validation_ok)
    assert row["level"] in CERTIFICATION_LEVELS
    return _persist(row)


def summary() -> dict[str, Any]:
    certs = get_certification()
    levels = {lvl: 0 for lvl in CERTIFICATION_LEVELS}
    for c in certs.values():
        levels[c.get("level") or "DEVELOPMENT"] = levels.get(c.get("level") or "DEVELOPMENT", 0) + 1
    certified = levels.get("CERTIFIED", 0)
    ready = levels.get("PRODUCTION_READY", 0) + certified
    return {
        "collectors": len(certs),
        "levels": levels,
        "certified_count": certified,
        "production_ready_or_above": ready,
        "all_certified": certified == len(COLLECTOR_SPECS),
        "consecutive_required": CERTIFIED_CONSECUTIVE_LIVE_RUNS,
        "fabricated": False,
    }
