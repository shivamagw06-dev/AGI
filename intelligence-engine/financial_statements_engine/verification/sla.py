"""Pipeline SLA / operational metrics (FSE-02.2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from financial_statements_engine.orchestrator.schema import STAGES
from financial_statements_engine.orchestrator.store import list_workflows
from financial_statements_engine.util import now_iso
from financial_statements_engine.verification.report import stage_timing


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return float(xs[f])
    return float(xs[f] + (xs[c] - xs[f]) * (k - f))


def _overall_ms(wf: dict[str, Any]) -> float | None:
    started = _parse_ts(wf.get("started_at") or wf.get("created_at"))
    finished = _parse_ts(wf.get("finished_at"))
    if started and finished:
        return max(0.0, (finished - started).total_seconds() * 1000.0)
    timings = stage_timing(wf)
    durs = [float(t["duration_ms"]) for t in timings.values() if t.get("duration_ms") is not None]
    return float(sum(durs)) if durs else None


def compute_sla_metrics(*, limit: int = 2000) -> dict[str, Any]:
    rows = list_workflows(limit=limit)
    queued = [w for w in rows if w.get("state") in ("QUEUED", "RECEIVED", "RETRYING")]
    completed = [w for w in rows if w.get("state") == "COMPLETED"]
    failed = [w for w in rows if w.get("state") == "FAILED"]
    dlq = [w for w in rows if w.get("state") == "DEAD_LETTER"]
    running = [w for w in rows if w.get("state") == "RUNNING"]

    durations = []
    stage_durs: dict[str, list[float]] = {s: [] for s in STAGES}
    stage_ok: dict[str, int] = {s: 0 for s in STAGES}
    stage_total: dict[str, int] = {s: 0 for s in STAGES}
    retried = 0

    for wf in rows:
        if int(wf.get("retries") or 0) > 0:
            retried += 1
        oms = _overall_ms(wf)
        if oms is not None and wf.get("state") in ("COMPLETED", "FAILED", "DEAD_LETTER"):
            durations.append(oms)
        timings = stage_timing(wf)
        for stage, t in timings.items():
            if t.get("status") in ("COMPLETED", "FAILED"):
                stage_total[stage] = stage_total.get(stage, 0) + 1
                if t.get("status") == "COMPLETED":
                    stage_ok[stage] = stage_ok.get(stage, 0) + 1
                if t.get("duration_ms") is not None:
                    stage_durs.setdefault(stage, []).append(float(t["duration_ms"]))

    oldest = None
    oldest_ts = None
    for w in queued:
        ts = _parse_ts(w.get("created_at") or w.get("updated_at"))
        if ts and (oldest_ts is None or ts < oldest_ts):
            oldest_ts = ts
            oldest = {
                "workflow_id": w.get("workflow_id"),
                "ticker": w.get("ticker"),
                "state": w.get("state"),
                "created_at": w.get("created_at"),
                "age_seconds": max(0, int((datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds())),
            }

    n_terminal = len(completed) + len(failed) + len(dlq)
    success_pct = round(100.0 * len(completed) / n_terminal, 2) if n_terminal else None
    retry_rate = round(100.0 * retried / len(rows), 2) if rows else 0.0
    dlq_rate = round(100.0 * len(dlq) / len(rows), 2) if rows else 0.0

    stage_success = {}
    for s in STAGES:
        tot = stage_total.get(s, 0)
        stage_success[s] = round(100.0 * stage_ok.get(s, 0) / tot, 2) if tot else None

    avg_stage = {s: (round(sum(v) / len(v), 2) if v else None) for s, v in stage_durs.items()}

    # Throughput: completed per hour over last 24h window if timestamps exist
    now = datetime.now(timezone.utc)
    recent_completed = 0
    for w in completed:
        ts = _parse_ts(w.get("finished_at"))
        if ts and (now - ts.astimezone(timezone.utc)).total_seconds() <= 86400:
            recent_completed += 1
    throughput_per_hour = round(recent_completed / 24.0, 3)

    return {
        "queue_depth": len(queued) + len(running),
        "queued": len(queued),
        "running": len(running),
        "oldest_queued_workflow": oldest,
        "average_workflow_duration_ms": round(sum(durations) / len(durations), 2) if durations else None,
        "p95_workflow_duration_ms": round(_percentile(durations, 95) or 0, 2) if durations else None,
        "retry_rate_pct": retry_rate,
        "dlq_rate_pct": dlq_rate,
        "workflow_success_pct": success_pct,
        "stage_success_pct": stage_success,
        "average_stage_duration_ms": avg_stage,
        "average_parse_ms": avg_stage.get("PARSE"),
        "average_validation_ms": avg_stage.get("VALIDATE"),
        "average_publish_ms": avg_stage.get("WAREHOUSE_PUBLISH"),
        "average_dme_ms": avg_stage.get("DERIVED_METRICS"),
        "throughput_per_hour_24h": throughput_per_hour,
        "counts": {
            "total": len(rows),
            "completed": len(completed),
            "failed": len(failed),
            "dead_letter": len(dlq),
            "retried_workflows": retried,
        },
        "as_of": now_iso(),
    }
