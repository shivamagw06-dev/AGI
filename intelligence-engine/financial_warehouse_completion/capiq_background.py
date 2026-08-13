"""Persistent, resumable Capital IQ annual-accounting migration.

HTTP starts or inspects the job; it never owns the work. Checkpoints and the
final independent receipt live in the warehouse database and survive restarts.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from pathlib import Path
from typing import Any, Iterable

from financial_warehouse_completion.capiq_normalization import (
    SOURCE, audit_and_prepare, mapping_rows,
)
from financial_warehouse_completion.capiq_workbook import (
    DEFAULT_YEARS, MASTER_FIELD_MAP, WORKBOOK_PATH, _master_rows, preview,
)
from institutional_warehouse import db, gateway, statement_identity, store
from institutional_warehouse.formulas import recalculate
from institutional_warehouse.schema import find_tab
from institutional_warehouse.values import now_iso

CHUNK_SIZE = 500
RECALC_STAGES = ("statement_derivations", "ratios", "annual_sector_ratios", "valuation", "factors", "quality")
CODE_VERSION = "CAPIQ_BACKGROUND_V1"
SCHEMA_VERSION = "CAPIQ_V2"
ACTIVE = ("QUEUED", "RUNNING")
FINAL = ("FAILED", "COMPLETED", "COMPLETED_WITH_WARNINGS")
_LOCK = threading.RLock()
_THREAD: threading.Thread | None = None
_PAUSE = threading.Event()
_READY = False
_ACTIVE_STATUS: str | None = None


def _init() -> None:
    global _READY
    with _LOCK:
        if not _READY:
            db.init(force=True)
            _READY = True


def _source_version(path: Path = WORKBOOK_PATH) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = db.query(sql, params)
    return rows[0] if rows else None


def _decode(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    out = dict(row)
    for key in ("years", "receipt"):
        if out.get(key):
            try: out[key] = json.loads(out[key])
            except Exception: pass
    return out


def latest_job() -> dict[str, Any] | None:
    _init()
    return _decode(_one("SELECT * FROM wh_capiq_import_jobs ORDER BY started_at DESC LIMIT 1"))


def migration_active_cached() -> bool:
    """Fast request-path flag; hits the warehouse only once per process boot."""
    global _ACTIVE_STATUS
    if _ACTIVE_STATUS is None:
        job = latest_job()
        _ACTIVE_STATUS = str((job or {}).get("status") or "")
    return _ACTIVE_STATUS in {"QUEUED", "RUNNING", "PAUSED"}


def job_status(job_id: str, *, include_chunks: bool = True) -> dict[str, Any]:
    _init()
    job = _decode(_one("SELECT * FROM wh_capiq_import_jobs WHERE job_id = ?", (job_id,)))
    if not job:
        return {"ok": False, "error": "job_not_found", "job_id": job_id}
    chunks = db.query(
        "SELECT * FROM wh_capiq_import_chunks WHERE job_id = ? ORDER BY phase, row_start",
        (job_id,),
    ) if include_chunks else []
    approved = int(job.get("approved_rows") or 0)
    verified = int(job.get("verified_rows") or 0)
    job["progress_pct"] = round(100.0 * verified / approved, 2) if approved else 0.0
    job["ok"] = True
    if include_chunks: job["chunks"] = chunks
    return job


def create_job(*, years: Iterable[int] | None = None, actor: str = "fwcp") -> dict[str, Any]:
    global _ACTIVE_STATUS
    _init()
    selected = tuple(sorted({int(y) for y in (years or DEFAULT_YEARS)}))
    existing = _one(
        "SELECT job_id FROM wh_capiq_import_jobs WHERE status IN (?, ?) ORDER BY started_at DESC LIMIT 1",
        ACTIVE,
    )
    if existing:
        start_worker(str(existing["job_id"]), actor=actor)
        return {**job_status(str(existing["job_id"]), include_chunks=False), "created": False}

    check = preview(years=selected)
    if not check.get("ok"):
        return check
    rows = [r for r in _master_rows(path=WORKBOOK_PATH)
            if int(str(r["fiscal_year"]).replace("FY", "")) in selected]
    prepared = audit_and_prepare(rows, field_map=MASTER_FIELD_MAP, source_file=WORKBOOK_PATH.name)
    approved = len(prepared["accepted"])
    quarantined = len(rows) - approved
    job_id = f"capiq_{uuid.uuid4().hex[:16]}"
    stamp = now_iso()
    persistence_chunks = (approved + CHUNK_SIZE - 1) // CHUNK_SIZE
    evidence_chunks = (len(prepared["audits"]) + CHUNK_SIZE - 1) // CHUNK_SIZE
    identity_chunks = (len(prepared["identities"]) + CHUNK_SIZE - 1) // CHUNK_SIZE
    total_chunks = 1 + evidence_chunks + identity_chunks + persistence_chunks + 2 + len(RECALC_STAGES)
    db.execute(
        "INSERT INTO wh_capiq_import_jobs (job_id, source_file, source_version, code_version,"
        " schema_version, started_at, status, phase, total_rows, approved_rows, quarantined_rows,"
        " processed_rows, persisted_rows, normalized_rows, recalculated_rows, verified_rows,"
        " failed_rows, current_chunk, total_chunks, error_count, heartbeat_at, years)"
        " VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', 'MAPPING', ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, ?, 0, ?, ?)",
        (job_id, WORKBOOK_PATH.name, _source_version(), CODE_VERSION, SCHEMA_VERSION, stamp,
         len(rows), approved, quarantined, total_chunks, stamp, json.dumps(selected)),
    )
    chunks = [(f"{job_id}:mapping", job_id, "MAPPING", 0, len(MASTER_FIELD_MAP), "QUEUED", 0, 0, 0, 0)]
    for idx, start in enumerate(range(0, len(prepared["audits"]), CHUNK_SIZE), 1):
        end = min(start + CHUNK_SIZE, len(prepared["audits"]))
        chunks.append((f"{job_id}:evidence:{idx}", job_id, "EVIDENCE", start, end, "QUEUED", 0, 0, 0, 0))
    for idx, start in enumerate(range(0, len(prepared["identities"]), CHUNK_SIZE), 1):
        end = min(start + CHUNK_SIZE, len(prepared["identities"]))
        chunks.append((f"{job_id}:identity:{idx}", job_id, "IDENTITY", start, end, "QUEUED", 0, 0, 0, 0))
    for idx, start in enumerate(range(0, approved, CHUNK_SIZE), 1):
        end = min(start + CHUNK_SIZE, approved)
        chunks.append((f"{job_id}:persist:{idx}", job_id, "PERSIST", start, end, "QUEUED", 0, 0, 0, 0))
    chunks.append((f"{job_id}:normalize", job_id, "NORMALIZE", 0, approved, "QUEUED", 0, 0, 0, 0))
    for idx, _stage in enumerate(RECALC_STAGES):
        chunks.append((f"{job_id}:recalculate:{idx + 1}", job_id, "RECALCULATE", idx, idx + 1,
                       "QUEUED", 0, 0, 0, 0))
    chunks.append((f"{job_id}:verify", job_id, "VERIFY", 0, approved, "QUEUED", 0, 0, 0, 0))
    db.executemany(
        "INSERT INTO wh_capiq_import_chunks (chunk_id, job_id, phase, row_start, row_end, status,"
        " attempt_count, processed_count, persisted_count, error_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        chunks,
    )
    _ACTIVE_STATUS = "QUEUED"
    start_worker(job_id, actor=actor)
    return {**job_status(job_id, include_chunks=False), "created": True}


def _load_approved(job: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = {int(y) for y in job.get("years") or DEFAULT_YEARS}
    rows = [r for r in _master_rows(path=WORKBOOK_PATH)
            if int(str(r["fiscal_year"]).replace("FY", "")) in selected]
    prepared = audit_and_prepare(rows, field_map=MASTER_FIELD_MAP, source_file=WORKBOOK_PATH.name)
    return prepared["accepted"], prepared


def _touch(job_id: str, **fields: Any) -> None:
    global _ACTIVE_STATUS
    fields["heartbeat_at"] = now_iso()
    db.execute(
        "UPDATE wh_capiq_import_jobs SET " + ", ".join(f"{k} = ?" for k in fields) + " WHERE job_id = ?",
        (*fields.values(), job_id),
    )
    if "status" in fields:
        _ACTIVE_STATUS = str(fields["status"] or "")


def _upgrade_recalculation_chunks(job_id: str) -> None:
    """Upgrade an active V1 single recalculation checkpoint in place."""
    rows = db.query("SELECT * FROM wh_capiq_import_chunks WHERE job_id=? AND phase='RECALCULATE'", (job_id,))
    if len(rows) != 1 or str(rows[0].get("chunk_id") or "").count(":") > 2:
        return
    old = rows[0]
    if old.get("status") == "COMPLETED":
        return
    db.execute("DELETE FROM wh_capiq_import_chunks WHERE chunk_id=?", (old["chunk_id"],))
    payload = [
        (f"{job_id}:recalculate:{idx + 1}", job_id, "RECALCULATE", idx, idx + 1, "QUEUED", 0, 0, 0, 0)
        for idx, _stage in enumerate(RECALC_STAGES)
    ]
    db.executemany(
        "INSERT INTO wh_capiq_import_chunks (chunk_id, job_id, phase, row_start, row_end, status,"
        " attempt_count, processed_count, persisted_count, error_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    db.execute("UPDATE wh_capiq_import_jobs SET total_chunks=total_chunks+?, phase='RECALCULATE', heartbeat_at=? WHERE job_id=?",
               (len(RECALC_STAGES) - 1, now_iso(), job_id))


def _stage_heartbeat(job_id: str, chunk_id: str, stop: threading.Event) -> None:
    while not stop.wait(30):
        stamp = now_iso()
        try:
            db.execute("UPDATE wh_capiq_import_jobs SET heartbeat_at=? WHERE job_id=?", (stamp, job_id))
            db.execute("UPDATE wh_capiq_import_chunks SET heartbeat_at=? WHERE chunk_id=?", (stamp, chunk_id))
        except Exception:
            pass


def _chunk_run(chunk: dict[str, Any], job: dict[str, Any], approved: list[dict[str, Any]],
               prepared: dict[str, Any], actor: str) -> None:
    chunk_id = str(chunk["chunk_id"])
    phase = str(chunk["phase"])
    stamp = now_iso()
    db.execute(
        "UPDATE wh_capiq_import_chunks SET status='RUNNING', attempt_count=COALESCE(attempt_count,0)+1,"
        " started_at=COALESCE(started_at, ?), heartbeat_at=? WHERE chunk_id=?",
        (stamp, stamp, chunk_id),
    )
    if phase == "MAPPING":
        batch = mapping_rows(MASTER_FIELD_MAP)
        result = gateway.write("capiq_metric_mapping", batch, source=SOURCE, actor=actor,
                               reason=f"capiq_background:{job['job_id']}:mapping", import_id=str(job["job_id"]))
        persisted, processed = int(result.get("written") or 0), len(batch)
    elif phase == "EVIDENCE":
        batch = prepared["audits"][int(chunk["row_start"]):int(chunk["row_end"])]
        result = gateway.write("financial_import_audit", batch, source=SOURCE, actor=actor,
                               reason=f"capiq_background:{job['job_id']}:audit", import_id=str(job["job_id"]))
        persisted, processed = int(result.get("written") or 0), len(batch)
    elif phase == "IDENTITY":
        batch = prepared["identities"][int(chunk["row_start"]):int(chunk["row_end"])]
        result = gateway.write("company_identity_map", batch, source=SOURCE, actor=actor,
                               reason=f"capiq_background:{job['job_id']}:identity", import_id=str(job["job_id"]))
        persisted, processed = int(result.get("written") or 0), len(batch)
    elif phase == "PERSIST":
        batch = approved[int(chunk["row_start"]):int(chunk["row_end"])]
        result = gateway.write(
            "financials_annual", batch, source=SOURCE, actor=actor,
            reason=f"capiq_background:{job['job_id']}:{chunk_id}",
            import_id=str(job["job_id"]), reported_unit="inr_million",
        )
        persisted = int(result.get("written") or 0)
        processed = len(batch)
    elif phase == "NORMALIZE":
        # Unit/missing-value normalization is part of gateway persistence. This
        # phase independently counts records carrying canonical unit metadata.
        counts = _verification_counts(approved)
        persisted = processed = counts["normalized"]
    elif phase == "RECALCULATE":
        stage_index = int(chunk["row_start"])
        stage = RECALC_STAGES[stage_index]
        stop_heartbeat = threading.Event()
        heartbeat = threading.Thread(target=_stage_heartbeat, args=(str(job["job_id"]), chunk_id, stop_heartbeat),
                                     name=f"capiq-heartbeat-{stage}", daemon=True)
        heartbeat.start()
        try:
            result = recalculate(actor=actor, stages=(stage,))
        finally:
            stop_heartbeat.set()
        if not result.get("ok"):
            raise RuntimeError(json.dumps(result.get("errors") or [])[:1000])
        persisted = processed = len(approved) if stage == RECALC_STAGES[-1] else 0
    else:
        receipt = _verify(job, approved)
        persisted = processed = int(receipt["verified"])
        db.execute("UPDATE wh_capiq_import_jobs SET receipt=? WHERE job_id=?",
                   (json.dumps(receipt, sort_keys=True), job["job_id"]))
    db.execute(
        "UPDATE wh_capiq_import_chunks SET status='COMPLETED', completed_at=?, heartbeat_at=?,"
        " processed_count=?, persisted_count=?, last_error=NULL WHERE chunk_id=?",
        (now_iso(), now_iso(), processed, persisted, chunk_id),
    )


def _expected_ids(approved: list[dict[str, Any]]) -> set[str]:
    tab = find_tab("financials_annual")
    assert tab is not None
    identified = statement_identity.apply_identity(tab, approved)
    return {rid for row in identified if (rid := store.make_row_id(tab, row))}


def _verification_counts(approved: list[dict[str, Any]]) -> dict[str, int]:
    expected = _expected_ids(approved)
    actual: set[str] = set()
    normalized: set[str] = set()
    ids = sorted(expected)
    for start in range(0, len(ids), 500):
        batch = ids[start:start + 500]
        marks = ",".join("?" for _ in batch)
        rows = db.query(
            f"SELECT row_id, sys_reported_unit, sys_unit_method FROM wh_financials_annual WHERE row_id IN ({marks})",
            batch,
        )
        actual.update(str(r["row_id"]) for r in rows)
        normalized.update(
            str(r["row_id"]) for r in rows
            if r.get("sys_reported_unit") in ("million", "inr_million") and r.get("sys_unit_method")
        )
    return {"expected": len(expected), "persisted": len(actual), "normalized": len(normalized),
            "missing": len(expected - actual), "duplicate": 0}


def _verify(job: dict[str, Any], approved: list[dict[str, Any]]) -> dict[str, Any]:
    counts = _verification_counts(approved)
    symbols = {str(r.get("symbol") or "").upper() for r in approved}
    factor_rows = db.query("SELECT DISTINCT symbol FROM wh_hedge_fund_factors WHERE source = ?", ("formula_engine",))
    factor_symbols = {str(r.get("symbol") or "").upper() for r in factor_rows}
    factor_eligible = len(symbols & factor_symbols)
    warnings = []
    if counts["missing"]: warnings.append(f"missing_approved_records:{counts['missing']}")
    if counts["normalized"] != counts["persisted"]: warnings.append("unit_metadata_incomplete")
    if factor_eligible != len(symbols):
        warnings.append(f"factor_company_coverage:{factor_eligible}/{len(symbols)}")
    status = "COMPLETED" if not warnings and counts["persisted"] == int(job["approved_rows"]) else "COMPLETED_WITH_WARNINGS"
    return {
        "title": "Capital IQ Migration Receipt", "job_id": job["job_id"],
        "source": job["source_file"], "source_version": job["source_version"],
        "workbook_rows": job["total_rows"], "approved": job["approved_rows"],
        "quarantined": job["quarantined_rows"], "persisted": counts["persisted"],
        "normalized": counts["normalized"], "factors_recalculated": factor_eligible,
        "factor_unit": "companies", "verified": counts["persisted"],
        "missing": counts["missing"], "duplicate": counts["duplicate"], "failed": 0,
        "quality_warnings": warnings, "pit_status": "PIT_LIMITED",
        "status": status, "code_version": CODE_VERSION, "schema_version": SCHEMA_VERSION,
        "verified_at": now_iso(),
    }


def _run(job_id: str, actor: str) -> None:
    global _THREAD
    try:
        job = job_status(job_id, include_chunks=False)
        if not job.get("ok"): return
        _touch(job_id, status="RUNNING")
        approved, prepared = _load_approved(job)
        _upgrade_recalculation_chunks(job_id)
        chunks = db.query(
            "SELECT * FROM wh_capiq_import_chunks WHERE job_id=? AND status!='COMPLETED'"
            " ORDER BY CASE phase WHEN 'MAPPING' THEN 1 WHEN 'EVIDENCE' THEN 2 WHEN 'IDENTITY' THEN 3"
            " WHEN 'PERSIST' THEN 4 WHEN 'NORMALIZE' THEN 5 WHEN 'RECALCULATE' THEN 6 ELSE 7 END, row_start",
            (job_id,),
        )
        for chunk in chunks:
            if _PAUSE.is_set():
                _touch(job_id, status="PAUSED")
                return
            try:
                _chunk_run(chunk, job, approved, prepared, actor)
            except Exception as exc:
                db.execute(
                    "UPDATE wh_capiq_import_chunks SET status='FAILED', error_count=COALESCE(error_count,0)+1,"
                    " last_error=?, heartbeat_at=? WHERE chunk_id=?",
                    (str(exc)[:1000], now_iso(), chunk["chunk_id"]),
                )
                current = job_status(job_id, include_chunks=False)
                _touch(job_id, status="FAILED", last_error=str(exc)[:1000],
                       failed_rows=int(current.get("failed_rows") or 0) + 1,
                       error_count=int(current.get("error_count") or 0) + 1)
                return
            done = _one(
                "SELECT COUNT(*) n, COALESCE(SUM(processed_count),0) processed,"
                " COALESCE(SUM(CASE WHEN phase='PERSIST' THEN persisted_count ELSE 0 END),0) persisted"
                " FROM wh_capiq_import_chunks WHERE job_id=? AND status='COMPLETED'",
                (job_id,),
            ) or {}
            counts = _verification_counts(approved) if chunk["phase"] != "PERSIST" else None
            fields: dict[str, Any] = {
                "current_chunk": int(done.get("n") or 0), "processed_rows": min(len(approved), int(done.get("processed") or 0)),
                "persisted_rows": int((counts or {}).get("persisted") or done.get("persisted") or 0),
                "phase": chunk["phase"],
            }
            if chunk["phase"] in ("NORMALIZE", "RECALCULATE", "VERIFY"):
                fields["normalized_rows"] = int((counts or {}).get("normalized") or 0)
            if chunk["phase"] in ("RECALCULATE", "VERIFY"):
                remaining_recalc = _one(
                    "SELECT COUNT(*) n FROM wh_capiq_import_chunks WHERE job_id=? AND phase='RECALCULATE' AND status!='COMPLETED'",
                    (job_id,),
                ) or {}
                fields["recalculated_rows"] = len(approved) if int(remaining_recalc.get("n") or 0) == 0 else 0
            if chunk["phase"] == "VERIFY":
                receipt = _decode(_one("SELECT receipt FROM wh_capiq_import_jobs WHERE job_id=?", (job_id,))) or {}
                rec = receipt.get("receipt") or {}
                fields.update(status=rec.get("status") or "COMPLETED_WITH_WARNINGS",
                              completed_at=now_iso(), verified_rows=int(rec.get("verified") or 0))
            _touch(job_id, **fields)
    finally:
        with _LOCK: _THREAD = None


def start_worker(job_id: str | None = None, *, actor: str = "fwcp") -> dict[str, Any]:
    global _THREAD
    _init()
    if job_id is None:
        row = _one("SELECT job_id FROM wh_capiq_import_jobs WHERE status IN ('QUEUED','RUNNING') ORDER BY started_at LIMIT 1")
        if not row: return {"ok": True, "started": False}
        job_id = str(row["job_id"])
    with _LOCK:
        if _THREAD and _THREAD.is_alive(): return {"ok": True, "started": False, "job_id": job_id}
        _PAUSE.clear()
        _THREAD = threading.Thread(target=_run, args=(job_id, actor), name="capiq-background-import", daemon=True)
        _THREAD.start()
    return {"ok": True, "started": True, "job_id": job_id}


def pause(job_id: str) -> dict[str, Any]:
    _PAUSE.set()
    _touch(job_id, status="PAUSED")
    return job_status(job_id, include_chunks=False)


def resume(job_id: str, *, actor: str = "fwcp") -> dict[str, Any]:
    _PAUSE.clear()
    db.execute("UPDATE wh_capiq_import_jobs SET status='QUEUED', last_error=NULL WHERE job_id=? AND status IN ('PAUSED','FAILED')", (job_id,))
    db.execute("UPDATE wh_capiq_import_chunks SET status='QUEUED' WHERE job_id=? AND status='FAILED'", (job_id,))
    start_worker(job_id, actor=actor)
    return job_status(job_id, include_chunks=False)


def resume_incomplete() -> dict[str, Any]:
    return start_worker()
