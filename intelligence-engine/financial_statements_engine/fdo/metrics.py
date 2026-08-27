"""Live ingestion, workflow, and source operational metrics (FDO)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from financial_statements_engine.fdo.inventory import raw_evidence_growth
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_jsonl(path: Path, limit: int = 10000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-max(1, limit) :]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def live_ingestion_metrics() -> dict[str, Any]:
    path = ensure_dirs() / "collection" / "ingest_metrics.jsonl"
    rows = _read_jsonl(path)
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    week_ago = now - timedelta(days=7)

    collected_today = 0
    collected_week = 0
    successful = 0
    failed = 0
    duplicates = 0
    download_lat: list[float] = []
    ingest_lat: list[float] = []
    companies_today: set[str] = set()

    for r in rows:
        ts = _parse_ts(r.get("ts"))
        action = str(r.get("action") or "")
        lat = r.get("latency_ms")
        if isinstance(lat, (int, float)):
            ingest_lat.append(float(lat))
        if ts and ts.date().isoformat() == today:
            collected_today += 1
            if r.get("ticker"):
                companies_today.add(str(r["ticker"]).upper())
        if ts and ts >= week_ago:
            collected_week += 1
        if action in {"stored", "restatement_candidate"}:
            successful += 1
        elif action in {"failed", "download_failed"}:
            failed += 1
        elif action == "duplicate_skipped":
            duplicates += 1

    # source metrics download latencies
    src_path = ensure_dirs() / "collection" / "source_metrics.jsonl"
    for r in _read_jsonl(src_path):
        if r.get("phase") == "download" and isinstance(r.get("latency_ms"), (int, float)):
            download_lat.append(float(r["latency_ms"]))
            if not r.get("ok"):
                failed += 1
            elif r.get("ok"):
                successful += 1

    # workflow durations from orchestrator
    wf_durs: list[float] = []
    try:
        from financial_statements_engine.orchestrator.store import list_workflows

        for wf in list_workflows(limit=2000):
            st = _parse_ts(wf.get("started_at") or wf.get("created_at"))
            fin = _parse_ts(wf.get("finished_at"))
            if st and fin:
                wf_durs.append(max(0.0, (fin - st).total_seconds() * 1000.0))
    except Exception:
        pass

    filings_hour = round(collected_today / max(1, now.hour + now.minute / 60.0), 3) if collected_today else 0.0

    return {
        "collected_today": collected_today,
        "collected_this_week": collected_week,
        "successful_downloads": successful,
        "failed_downloads": failed,
        "duplicate_filings": duplicates,
        "average_download_latency_ms": round(sum(download_lat) / len(download_lat), 2) if download_lat else None,
        "average_ingest_latency_ms": round(sum(ingest_lat) / len(ingest_lat), 2) if ingest_lat else None,
        "average_e2e_workflow_duration_ms": round(sum(wf_durs) / len(wf_durs), 2) if wf_durs else None,
        "filings_per_hour": filings_hour,
        "companies_today": len(companies_today),
        "companies_per_day": len(companies_today),
        "as_of": now_iso(),
    }


def source_health_metrics() -> dict[str, Any]:
    path = ensure_dirs() / "collection" / "source_metrics.jsonl"
    rows = _read_jsonl(path)
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = str(r.get("source_id") or r.get("source") or "unknown")
        b = by.setdefault(
            sid,
            {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "fallbacks": 0,
                "latencies": [],
                "last_success": None,
                "last_failure": None,
            },
        )
        b["attempts"] += 1
        ts = r.get("ts")
        if r.get("ok"):
            b["successes"] += 1
            b["last_success"] = ts or b["last_success"]
        else:
            b["failures"] += 1
            b["last_failure"] = ts or b["last_failure"]
        if r.get("fallback"):
            b["fallbacks"] += 1
        if isinstance(r.get("latency_ms"), (int, float)):
            b["latencies"].append(float(r["latency_ms"]))

    # Merge registry health if FSE-02.3 present
    registry_rows = []
    try:
        from financial_statements_engine.collection.source_layer.registry import registry_rows as reg_rows

        registry_rows = reg_rows()
    except Exception:
        registry_rows = []

    sources = []
    ids = set(by) | {r.get("source_id") for r in registry_rows}
    for sid in sorted(x for x in ids if x):
        b = by.get(sid) or {"attempts": 0, "successes": 0, "failures": 0, "fallbacks": 0, "latencies": [], "last_success": None, "last_failure": None}
        attempts = b["attempts"] or 0
        reg = next((r for r in registry_rows if r.get("source_id") == sid), {})
        sources.append(
            {
                "source_id": sid,
                "source_name": reg.get("source_name") or sid,
                "priority": reg.get("priority"),
                "availability": reg.get("health") or ("ok" if b["successes"] else "unknown"),
                "success_pct": round(100.0 * b["successes"] / attempts, 2) if attempts else None,
                "failure_pct": round(100.0 * b["failures"] / attempts, 2) if attempts else None,
                "latency_ms": round(sum(b["latencies"]) / len(b["latencies"]), 2) if b["latencies"] else None,
                "fallback_rate_pct": round(100.0 * b["fallbacks"] / attempts, 2) if attempts else None,
                "last_success": b["last_success"],
                "last_failure": b["last_failure"],
                "status": reg.get("status") or "observed",
            }
        )

    return {
        "sources": sources,
        "n": len(sources),
        "as_of": now_iso(),
    }


def workflow_ops_snapshot() -> dict[str, Any]:
    try:
        from financial_statements_engine.orchestrator.store import count_by_state, list_workflows

        counts = count_by_state()
        queue_depth = sum(counts.get(s, 0) for s in ("QUEUED", "RECEIVED", "RETRYING", "RUNNING"))
        dlq = counts.get("DEAD_LETTER", 0)
        completed = counts.get("COMPLETED", 0)
        failed = counts.get("FAILED", 0)
        durs = []
        for wf in list_workflows(limit=500):
            st = _parse_ts(wf.get("started_at") or wf.get("created_at"))
            fin = _parse_ts(wf.get("finished_at"))
            if st and fin:
                durs.append((fin - st).total_seconds() * 1000.0)
        return {
            "queue_depth": queue_depth,
            "dlq_size": dlq,
            "completed": completed,
            "failed": failed,
            "counts_by_state": counts,
            "average_workflow_duration_ms": round(sum(durs) / len(durs), 2) if durs else None,
            "throughput_completed": completed,
        }
    except Exception:
        return {"queue_depth": 0, "dlq_size": 0, "completed": 0, "failed": 0}


def ops_bundle() -> dict[str, Any]:
    return {
        "ingestion": live_ingestion_metrics(),
        "sources": source_health_metrics(),
        "workflows": workflow_ops_snapshot(),
        "raw_evidence": raw_evidence_growth(),
        "as_of": now_iso(),
    }
