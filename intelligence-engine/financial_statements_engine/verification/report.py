"""Immutable workflow reports (FSE-02.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from financial_statements_engine.orchestrator.schema import STAGES
from financial_statements_engine.orchestrator.store import load_workflow
from financial_statements_engine.util import now_iso
from financial_statements_engine.verification.schema import PIPELINE_CHECKLIST, VERSION, WORKSTREAM_ID
from financial_statements_engine.verification.store import save_report


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(started: str | None, finished: str | None, explicit: Any = None) -> int | None:
    if isinstance(explicit, (int, float)):
        return int(explicit)
    a, b = _parse_ts(started), _parse_ts(finished)
    if a and b:
        return max(0, int((b - a).total_seconds() * 1000))
    return None


def stage_timing(wf: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    stages = wf.get("stages") or {}
    for stage in STAGES:
        meta = stages.get(stage) or {}
        out[stage] = {
            "stage": stage,
            "status": meta.get("status") or "PENDING",
            "started_at": meta.get("started_at"),
            "finished_at": meta.get("finished_at"),
            "duration_ms": _duration_ms(meta.get("started_at"), meta.get("finished_at"), meta.get("duration_ms")),
            "retry_count": max(0, int(meta.get("attempts") or 0) - (1 if meta.get("status") == "COMPLETED" else 0)),
            "attempts": int(meta.get("attempts") or 0),
            "error": meta.get("error"),
            "skipped_idempotent": bool(meta.get("skipped_idempotent")),
        }
    return out


def checklist_from_workflow(wf: dict[str, Any]) -> dict[str, Any]:
    timings = stage_timing(wf)
    items = []
    all_ok = True
    for label, stage in PIPELINE_CHECKLIST:
        t = timings.get(stage) or {}
        ok = t.get("status") == "COMPLETED"
        if not ok:
            all_ok = False
        items.append(
            {
                "checkpoint": label,
                "stage": stage,
                "ok": ok,
                "status": t.get("status"),
                "started_at": t.get("started_at"),
                "finished_at": t.get("finished_at"),
                "duration_ms": t.get("duration_ms"),
                "retry_count": t.get("retry_count"),
                "attempts": t.get("attempts"),
            }
        )
    return {
        "workflow_created": bool(wf.get("workflow_id") and wf.get("created_at")),
        "all_stages_ok": all_ok and wf.get("state") == "COMPLETED",
        "items": items,
    }


def build_workflow_report(wf: dict[str, Any]) -> dict[str, Any]:
    timings = stage_timing(wf)
    stage_durs = [t["duration_ms"] for t in timings.values() if t.get("duration_ms") is not None]
    overall = _duration_ms(wf.get("started_at") or wf.get("created_at"), wf.get("finished_at"))
    if overall is None and stage_durs:
        overall = sum(stage_durs)

    retry_history = []
    for h in wf.get("history") or []:
        if h.get("state") in ("RETRYING", "QUEUED") or h.get("replay"):
            retry_history.append(h)
    for stage, t in timings.items():
        if int(t.get("attempts") or 0) > 1:
            retry_history.append(
                {
                    "stage": stage,
                    "attempts": t.get("attempts"),
                    "error": t.get("error"),
                }
            )

    dl = wf.get("dead_letter")
    report = {
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "workflow_id": wf.get("workflow_id"),
        "company": wf.get("ticker") or wf.get("company_id"),
        "company_id": wf.get("company_id"),
        "filing": wf.get("filing_type") or wf.get("document_type"),
        "period": wf.get("period"),
        "source": wf.get("source"),
        "document_hash": wf.get("document_hash"),
        "evidence_id": wf.get("evidence_id"),
        "document_type": wf.get("document_type"),
        "final_status": wf.get("state"),
        "current_stage": wf.get("current_stage"),
        "failure_reason": wf.get("failure_reason"),
        "retries": int(wf.get("retries") or 0),
        "retry_history": retry_history,
        "dlq_status": {
            "in_dlq": wf.get("state") == "DEAD_LETTER" or bool(dl),
            "dead_letter": dl,
        },
        "stage_timestamps": timings,
        "overall_duration_ms": overall,
        "created_at": wf.get("created_at"),
        "started_at": wf.get("started_at"),
        "finished_at": wf.get("finished_at"),
        "checklist": checklist_from_workflow(wf),
        "generated_at": now_iso(),
    }
    return report


def generate_workflow_report(workflow_id: str, *, persist: bool = True) -> dict[str, Any]:
    wf = load_workflow(workflow_id)
    if not wf:
        return {"ok": False, "error": "workflow_not_found", "workflow_id": workflow_id}
    report = build_workflow_report(wf)
    path = None
    if persist:
        path = str(save_report(report))
    return {"ok": True, "report": report, "path": path}
