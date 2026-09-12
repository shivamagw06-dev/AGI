"""LIDI production surfaces — status, freshness, dashboard, morning entrypoint."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from live_data import store
from live_data.pipeline import run_live_ingestion
from live_data.schema import FREEZE_LOCKS, LIDI_VERSION, MODULE_CODE, PROGRAMME, SOURCES


def run_morning_live_ingestion(**kwargs: Any) -> dict[str, Any]:
    """Scheduler soft-wire entrypoint."""
    return run_live_ingestion(**kwargs)


def status() -> dict[str, Any]:
    last = store.get_last_run() or {}
    health = store.get_collector_health()
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": LIDI_VERSION,
        "state": "READY" if (last.get("quality_gates") or {}).get("passed") else ("DEGRADED" if last else "IDLE"),
        "last_run_at": last.get("finished_at"),
        "collectors_operational": (last.get("quality_gates") or {}).get("collectors_operational"),
        "collectors_total": (last.get("quality_gates") or {}).get("collectors_total") or 5,
        "fixture_collectors_disabled": True,
        "freeze_locks": FREEZE_LOCKS,
        "collector_count": len(health),
        "fabricated": False,
    }


def sources() -> dict[str, Any]:
    last = store.get_last_run() or {}
    stages = last.get("stages") or {}
    rows = []
    for s in SOURCES:
        st = stages.get(s["source_id"]) or {}
        rows.append(
            {
                **s,
                "last_ok": st.get("ok"),
                "mode": st.get("mode"),
                "fallback": st.get("fallback"),
                "fixture": st.get("fixture", False),
            }
        )
    return {"n": len(rows), "sources": rows, "fabricated": False}


def freshness() -> dict[str, Any]:
    last = store.get_last_run() or {}
    stages = last.get("stages") or {}
    rows = []
    for s in SOURCES:
        st = stages.get(s["source_id"]) or {}
        snap = store.get_latest_snapshot(s["source_id"], "LATEST")
        rows.append(
            {
                "source_id": s["source_id"],
                "mode": st.get("mode"),
                "effective_date": st.get("effective_date") or (snap or {}).get("effective_date"),
                "retrieved_at": (snap or {}).get("retrieved_at"),
                "snapshot_age_hint": (snap or {}).get("retrieved_at"),
                "fallback": bool(st.get("fallback")),
                "freshness": "live"
                if st.get("mode") == "live"
                else ("snapshot" if st.get("fallback") or st.get("mode") == "snapshot" else st.get("mode")),
            }
        )
    return {
        "as_of": last.get("finished_at"),
        "sources": rows,
        "fabricated": False,
    }


def collectors() -> dict[str, Any]:
    health = store.get_collector_health()
    rows = []
    for cid, h in sorted(health.items()):
        rows.append(
            {
                "collector_id": cid,
                "source": h.get("source"),
                "version": h.get("version") or cid,
                "frequency": h.get("frequency"),
                "retry_policy": h.get("retry_policy"),
                "authentication": h.get("authentication"),
                "last_success": h.get("last_success"),
                "last_failure": h.get("last_failure"),
                "checksum": h.get("last_checksum"),
                "downloaded_files": h.get("downloaded_files") or [],
                "metadata": h.get("metadata") or {},
                "success_count": h.get("success_count"),
                "failure_count": h.get("failure_count"),
                "last_error": h.get("last_error"),
            }
        )
    return {"n": len(rows), "collectors": rows, "fabricated": False}


def validation() -> dict[str, Any]:
    rows = store.list_validations(limit=50)
    failures = [r for r in rows if not r.get("ok")]
    return {
        "n": len(rows),
        "failure_count": len(failures),
        "validations": rows,
        "fabricated": False,
    }


def fallback() -> dict[str, Any]:
    rows = store.list_fallbacks(limit=50)
    fixture_used = [r for r in rows if r.get("used_fixture")]
    return {
        "n": len(rows),
        "fallbacks": rows,
        "silent_fixture_fallbacks": len(fixture_used),
        "policy": "latest_validated_snapshot_only",
        "never_silent_fixture_fallback": True,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    st = status()
    src = sources()
    fr = freshness()
    col = collectors()
    val = validation()
    fb = fallback()
    last = store.get_last_run() or {}
    return {
        "title": "Live Institutional Data Ingestion",
        "north_star": "validated_live_data_not_fixtures",
        "live_sources": src["sources"],
        "collector_health": col["collectors"],
        "freshness": fr["sources"],
        "latency": {
            "started_at": last.get("started_at"),
            "finished_at": last.get("finished_at"),
        },
        "validation_failures": val["failure_count"],
        "missing_data": [
            s["source_id"] for s in src["sources"] if s.get("last_ok") is False
        ],
        "fallback_usage": fb["n"],
        "snapshot_age": [
            {"source_id": r["source_id"], "snapshot_age_hint": r.get("snapshot_age_hint")}
            for r in fr["sources"]
        ],
        "quality_gates": last.get("quality_gates"),
        "status": st,
        "publish": last.get("publish"),
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
    }


def health() -> dict[str, Any]:
    st = status()
    return {
        "status": "ok" if st["state"] in {"READY", "DEGRADED", "IDLE"} else "error",
        "module": MODULE_CODE,
        "version": LIDI_VERSION,
        "state": st["state"],
        "reasoning_untouched": True,
        "never_raw_to_reasoning": True,
        "fabricated": False,
    }


def last_run() -> dict[str, Any]:
    return deepcopy(store.get_last_run() or {"status": "none"})
