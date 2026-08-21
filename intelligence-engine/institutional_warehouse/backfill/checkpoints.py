"""Resumable state for the backfill engine.

Two kinds of work, two kinds of bookmark:

* **Date work** (NSE archive) — a trading day is fetched once. ``wh_backfill_dates``
  holds one row per (source, date) so a completed day is never downloaded again,
  which is the whole reason 406 downloads only ever produced 3 trading days.
* **Entity work** (Yahoo per company) — a company is walked from its most recent
  covered period backwards. ``wh_backfill_checkpoints`` holds the cursor, the
  attempt count and the last error so an interrupted run resumes where it left
  off instead of starting again.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse import db
from institutional_warehouse.values import now_iso

DONE = "done"
PENDING = "pending"
FAILED = "failed"
SKIPPED = "skipped"
RUNNING = "running"

MAX_ATTEMPTS = 3


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:32]


# --------------------------------------------------------------------------
# Date work
# --------------------------------------------------------------------------


def date_status(source: str, trade_date: str) -> Optional[dict[str, Any]]:
    rows = db.query(
        "SELECT * FROM wh_backfill_dates WHERE source = ? AND trade_date = ?",
        (source, trade_date),
    )
    return rows[0] if rows else None


def completed_dates(source: str) -> set[str]:
    rows = db.query(
        "SELECT trade_date FROM wh_backfill_dates WHERE source = ? AND status IN (?, ?)",
        (source, DONE, SKIPPED),
    )
    return {str(r["trade_date"]) for r in rows}


def exhausted_dates(source: str, max_attempts: int = MAX_ATTEMPTS) -> set[str]:
    rows = db.query(
        "SELECT trade_date FROM wh_backfill_dates WHERE source = ? AND status = ? AND attempts >= ?",
        (source, FAILED, int(max_attempts)),
    )
    return {str(r["trade_date"]) for r in rows}


def claim_dates(
    source: str,
    candidates: Sequence[str],
    *,
    limit: int = 20,
    max_attempts: int = MAX_ATTEMPTS,
) -> list[str]:
    """Return the next dates worth fetching, skipping done and exhausted ones."""
    db.init()
    skip = completed_dates(source) | exhausted_dates(source, max_attempts)
    claimed = [d for d in candidates if d not in skip]
    return claimed[: max(0, int(limit))]


def mark_date(
    source: str,
    trade_date: str,
    *,
    status: str,
    rows: int = 0,
    checksum: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    db.init()
    existing = date_status(source, trade_date)
    attempts = int((existing or {}).get("attempts") or 0) + 1
    if existing:
        db.execute(
            "UPDATE wh_backfill_dates SET status = ?, rows = ?, checksum = ?, attempts = ?,"
            " last_error = ?, updated_at = ? WHERE source = ? AND trade_date = ?",
            (status, int(rows), checksum, attempts, error, now_iso(), source, trade_date),
        )
        return
    db.execute(
        "INSERT INTO wh_backfill_dates (id, source, trade_date, status, rows, checksum,"
        " attempts, last_error, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (_id(source, trade_date), source, trade_date, status, int(rows), checksum,
         attempts, error, now_iso()),
    )


def frontier_date(source: str) -> Optional[str]:
    """The oldest day this source has actually collected.

    The walker generates its candidates as a fixed number of weekdays counted
    backwards, and counting from today caps how far back it can ever look -
    about eleven months at the scheduled slice size. It reached 2022 only
    because someone passed an explicit start by hand.

    Counting from the oldest collected day instead means each slice begins where
    the last one stopped, so the window travels with the work rather than
    staying pinned to the present.
    """
    rows = db.query(
        "SELECT MIN(trade_date) AS oldest FROM wh_backfill_dates"
        " WHERE source = ? AND status IN (?, ?)",
        (source, DONE, SKIPPED),
    )
    oldest = (rows[0] if rows else {}).get("oldest")
    return str(oldest) if oldest else None


def reopen_dates(
    source: str,
    *,
    reason: str,
    before: Optional[str] = None,
    after: Optional[str] = None,
) -> dict[str, Any]:
    """Mark already-collected days as needing another pass.

    A day is claimed once and never again, which is right when the collector is
    right. It is wrong after a fix that changes what a day contains: the bhavcopy
    parser kept only EQ and BE, so 928 days were stored without the companies
    that had been moved to the surveillance series on their way to being
    delisted - the exact rows the collector exists to capture.

    Attempts are reset to zero along with the status. A day that had failed twice
    is not two-thirds of the way to being abandoned once the reason it failed has
    been changed underneath it.

    Nothing is deleted. The re-run writes through the same upsert, so a day comes
    back with its existing rows updated and the missing ones added. Deleting
    first would leave a hole for as long as the re-run takes, and a re-run that
    stalls halfway would leave it permanently.
    """
    db.init()
    reason = str(reason or "").strip()
    if not reason:
        return {"ok": False, "error": "reason_required"}

    where = ["source = ?"]
    params: list[Any] = [source]
    if before:
        where.append("trade_date < ?")
        params.append(str(before))
    if after:
        where.append("trade_date > ?")
        params.append(str(after))
    clause = " AND ".join(where)

    affected = db.query(
        f"SELECT COUNT(*) AS n, MIN(trade_date) AS lo, MAX(trade_date) AS hi"
        f" FROM wh_backfill_dates WHERE {clause}",
        tuple(params),
    )
    summary = affected[0] if affected else {}
    db.execute(
        f"UPDATE wh_backfill_dates SET status = ?, attempts = 0, last_error = ?,"
        f" updated_at = ? WHERE {clause}",
        (PENDING, f"reopened: {reason}"[:400], now_iso(), *params),
    )
    return {
        "ok": True,
        "source": source,
        "reopened": int(summary.get("n") or 0),
        "oldest": summary.get("lo"),
        "newest": summary.get("hi"),
        "reason": reason,
    }


def reopen_entities(kind: str, *, reason: str) -> dict[str, Any]:
    """Put finished companies back in the queue.

    A company is fetched once and then skipped forever, which is right until a
    fix changes what its history contains. The bhavcopy walker overwrote Upstox's
    split-adjusted prices with raw ones across 2022-12-27 to 2025-09-01, and
    every affected company is checkpointed as complete - so the scheduler runs
    its slice, finds nothing owed, and reports success having repaired nothing.

    Marking them pending lets the ordinary scheduled slice do the repair, rather
    than it depending on somebody remembering to pass a flag.
    """
    db.init()
    reason = str(reason or "").strip()
    if not reason:
        return {"ok": False, "error": "reason_required"}
    counted = db.query(
        "SELECT COUNT(*) AS n FROM wh_backfill_checkpoints WHERE kind = ? AND status = ?",
        (kind, DONE),
    )
    total = int((counted[0] if counted else {}).get("n") or 0)
    db.execute(
        "UPDATE wh_backfill_checkpoints SET status = ?, attempts = 0, last_error = ?,"
        " updated_at = ? WHERE kind = ? AND status = ?",
        (PENDING, f"reopened: {reason}"[:400], now_iso(), kind, DONE),
    )
    return {"ok": True, "kind": kind, "reopened": total, "reason": reason}


def entity_progress(kind: str) -> dict[str, Any]:
    """How far a repair has got: done against everything it has to touch."""
    db.init()
    rows = db.query(
        "SELECT status, COUNT(*) AS n FROM wh_backfill_checkpoints WHERE kind = ?"
        " GROUP BY status", (kind,),
    ) or []
    by_status = {str(r["status"]): int(r["n"]) for r in rows}
    total = sum(by_status.values())
    done = by_status.get(DONE, 0)
    # Named, not just counted. A repair reported as "2,426 of 2,431" leaves five
    # companies keeping the wrong prices and no way to see which.
    stuck = db.query(
        "SELECT entity, attempts, last_error, updated_at FROM wh_backfill_checkpoints"
        " WHERE kind = ? AND status = ? ORDER BY updated_at DESC LIMIT 25",
        (kind, FAILED),
    ) or []
    return {"ok": True, "kind": kind, "by_status": by_status, "done": done,
            "total": total,
            "pct": round(100.0 * done / total, 1) if total else None,
            "failed": [{"entity": r.get("entity"), "attempts": r.get("attempts"),
                        "error": str(r.get("last_error") or "")[:200]} for r in stuck]}


def date_coverage(source: str) -> dict[str, Any]:
    rows = db.query(
        "SELECT status, COUNT(*) AS n, SUM(rows) AS r FROM wh_backfill_dates"
        " WHERE source = ? GROUP BY status",
        (source,),
    )
    span = db.query(
        "SELECT MIN(trade_date) AS a, MAX(trade_date) AS b FROM wh_backfill_dates"
        " WHERE source = ? AND status = ?",
        (source, DONE),
    )
    by_status = {str(r["status"]): int(r["n"] or 0) for r in rows}
    return {
        "source": source,
        "by_status": by_status,
        "days_done": by_status.get(DONE, 0),
        "rows_imported": int(sum(int(r["r"] or 0) for r in rows)),
        "oldest": (span[0].get("a") if span else None),
        "newest": (span[0].get("b") if span else None),
    }


# --------------------------------------------------------------------------
# Entity work
# --------------------------------------------------------------------------


def checkpoint(kind: str, entity: str) -> Optional[dict[str, Any]]:
    rows = db.query(
        "SELECT * FROM wh_backfill_checkpoints WHERE kind = ? AND entity = ?",
        (kind, str(entity).upper()),
    )
    return rows[0] if rows else None


def save_checkpoint(
    kind: str,
    entity: str,
    *,
    status: str,
    cursor: Optional[str] = None,
    rows_written: int = 0,
    first_period: Optional[str] = None,
    last_period: Optional[str] = None,
    error: Optional[str] = None,
    reset_attempts: bool = False,
) -> None:
    db.init()
    ticker = str(entity).upper()
    existing = checkpoint(kind, ticker)
    attempts = 0 if reset_attempts else int((existing or {}).get("attempts") or 0) + 1
    written = int((existing or {}).get("rows_written") or 0) + int(rows_written)
    if existing:
        db.execute(
            "UPDATE wh_backfill_checkpoints SET status = ?, cursor = ?, attempts = ?,"
            " rows_written = ?, first_period = ?, last_period = ?, last_error = ?, updated_at = ?"
            " WHERE kind = ? AND entity = ?",
            (status, cursor, attempts, written,
             first_period or existing.get("first_period"),
             last_period or existing.get("last_period"),
             error, now_iso(), kind, ticker),
        )
        return
    db.execute(
        "INSERT INTO wh_backfill_checkpoints (id, kind, entity, cursor, status, attempts,"
        " rows_written, first_period, last_period, last_error, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (_id(kind, ticker), kind, ticker, cursor, status, attempts, written,
         first_period, last_period, error, now_iso()),
    )


def pending_entities(
    kind: str,
    universe: Iterable[str],
    *,
    limit: int = 50,
    max_attempts: int = MAX_ATTEMPTS,
    refresh_done: bool = False,
) -> list[str]:
    """Companies still owed work, newest failures last so one bad name cannot block the queue."""
    db.init()
    states = {
        str(r["entity"]): r
        for r in db.query("SELECT * FROM wh_backfill_checkpoints WHERE kind = ?", (kind,))
    }
    fresh: list[str] = []
    retry: list[str] = []
    for raw in universe:
        ticker = str(raw).upper()
        state = states.get(ticker)
        if state is None:
            fresh.append(ticker)
            continue
        status = str(state.get("status") or "")
        if status == DONE and not refresh_done:
            continue
        if status == SKIPPED:
            continue
        if int(state.get("attempts") or 0) >= max_attempts and status == FAILED:
            continue
        retry.append(ticker)
    return (fresh + retry)[: max(0, int(limit))]


def entity_coverage(kind: str) -> dict[str, Any]:
    rows = db.query(
        "SELECT status, COUNT(*) AS n, SUM(rows_written) AS r FROM wh_backfill_checkpoints"
        " WHERE kind = ? GROUP BY status",
        (kind,),
    )
    by_status = {str(r["status"]): int(r["n"] or 0) for r in rows}
    return {
        "kind": kind,
        "by_status": by_status,
        "companies_done": by_status.get(DONE, 0),
        "companies_failed": by_status.get(FAILED, 0),
        "rows_written": int(sum(int(r["r"] or 0) for r in rows)),
    }


def failures(kind: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
    clause = " AND kind = ?" if kind else ""
    params: tuple[Any, ...] = (FAILED, kind) if kind else (FAILED,)
    rows = db.query(
        f"SELECT kind, entity, attempts, last_error, updated_at FROM wh_backfill_checkpoints"
        f" WHERE status = ?{clause} ORDER BY updated_at DESC LIMIT ?",
        (*params, max(1, int(limit))),
    )
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------


def start_job(kind: str, *, actor: str, params: Optional[dict[str, Any]] = None) -> str:
    db.init()
    job_id = uuid.uuid4().hex
    stamp = now_iso()
    db.execute(
        "INSERT INTO wh_backfill_jobs (id, created_at, updated_at, kind, actor, status, params,"
        " stats, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (job_id, stamp, stamp, kind, actor, RUNNING, json.dumps(params or {}, default=str),
         "{}", None),
    )
    return job_id


def finish_job(job_id: str, *, ok: bool, stats: dict[str, Any], error: Optional[str] = None) -> None:
    stamp = now_iso()
    db.execute(
        "UPDATE wh_backfill_jobs SET status = ?, updated_at = ?, finished_at = ?, stats = ?,"
        " error = ? WHERE id = ?",
        (DONE if ok else FAILED, stamp, stamp, json.dumps(stats, default=str), error, job_id),
    )


def recent_jobs(*, kind: Optional[str] = None, limit: int = 20) -> list[dict[str, Any]]:
    clause = " WHERE kind = ?" if kind else ""
    params: tuple[Any, ...] = (kind,) if kind else ()
    rows = db.query(
        f"SELECT * FROM wh_backfill_jobs{clause} ORDER BY created_at DESC LIMIT ?",
        (*params, max(1, int(limit))),
    )
    out = []
    for row in rows:
        out.append(
            {
                **row,
                "params": _loads(row.get("params"), {}),
                "stats": _loads(row.get("stats"), {}),
            }
        )
    return out


def _loads(raw: Any, fallback: Any) -> Any:
    try:
        return json.loads(raw) if raw else fallback
    except Exception:
        return fallback
