"""Collection job model and durable queue (FSE-02 §8)."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from financial_statements_engine.collection.schema import DOCUMENT_TYPES, JOB_STATUSES, MODES, PERIOD_TYPES
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def deterministic_job_id(
    *,
    ticker: str,
    source: str,
    document_type: str,
    period_type: str | None,
    period_end: str | None,
    mode: str,
) -> str:
    raw = "|".join(
        [
            str(ticker).upper().strip(),
            str(source),
            str(document_type),
            str(period_type or "unknown"),
            str(period_end or "unknown"),
            str(mode),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def make_job(
    *,
    ticker: str,
    source: str,
    document_type: str = "xbrl",
    period_type: str = "unknown",
    period_end: str | None = None,
    mode: str = "live",
    priority: int = 100,
    entity: str | None = None,
    discovery_ref: str | None = None,
    url: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    if document_type not in DOCUMENT_TYPES:
        document_type = "unknown"
    if period_type not in PERIOD_TYPES:
        period_type = "unknown"
    if mode not in MODES:
        mode = "live"
    jid = job_id or deterministic_job_id(
        ticker=ticker,
        source=source,
        document_type=document_type,
        period_type=period_type,
        period_end=period_end,
        mode=mode,
    )
    return {
        "job_id": jid,
        "ticker": str(ticker).upper().strip(),
        "entity": entity or str(ticker).upper().strip(),
        "source": source,
        "document_type": document_type,
        "period_type": period_type,
        "period_end": period_end,
        "mode": mode,
        "priority": int(priority),
        "attempt": 0,
        "discovery_ref": discovery_ref,
        "url": url,
        "status": "queued",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "error": None,
    }


def _jobs_dir():
    root = ensure_dirs()
    d = root / "collection" / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_job(job: dict[str, Any]) -> dict[str, Any]:
    job = dict(job)
    job["updated_at"] = now_iso()
    if job.get("status") not in JOB_STATUSES:
        raise ValueError(f"invalid job status: {job.get('status')}")
    path = _jobs_dir() / f"{job['job_id']}.json"
    write_json_atomic(path, job)
    # append queue index
    q = ensure_dirs() / "collection" / "queue.jsonl"
    q.parent.mkdir(parents=True, exist_ok=True)
    with q.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"job_id": job["job_id"], "status": job["status"], "ts": now_iso()}, sort_keys=True) + "\n")
    return job


def load_job(job_id: str) -> dict[str, Any] | None:
    path = _jobs_dir() / f"{job_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_status(job: dict[str, Any], status: str, **extra: Any) -> dict[str, Any]:
    job = dict(job)
    job["status"] = status
    job.update(extra)
    return save_job(job)


def dead_letter(job: dict[str, Any], detail: str) -> dict[str, Any]:
    job = set_status(job, "dead_letter", error=detail)
    path = ensure_dirs() / "collection" / "dead_letter.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"job_id": job["job_id"], "detail": detail, "ts": now_iso()}, sort_keys=True) + "\n")
    return job


def new_uuid() -> str:
    return str(uuid.uuid4())
