"""The durable queue of companies owed a statement refresh.

Durable from the first line, because today already showed why. A twenty-minute
ratio sweep was killed mid-run by a deploy and lost everything it had collected,
having kept its progress in the request. A queue of five hundred pending company
refreshes must survive the same event without anybody noticing it happened.

Each entry records the period that prompted it and what prompted it. A queue
nobody can explain is a queue nobody will trust enough to drain: "why is
HDFCBANK in here" has to have an answer that is not "someone must have added
it".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

TAB = "fundamentals_refresh_queue"
SOURCE = "fundamentals_refresh"

PENDING = "PENDING"
RUNNING = "RUNNING"
SUCCESS = "SUCCESS"
RETRY = "RETRY"
FAILED = "FAILED"

# States a worker may pick up. RUNNING is deliberately absent: an entry left
# RUNNING by a process that died is recovered explicitly rather than raced for.
CLAIMABLE = (PENDING, RETRY)

# After this many attempts a company is left alone until someone looks. Retrying
# a company whose ISIN Upstox does not recognise, forever, is not resilience.
MAX_ATTEMPTS = 3

# An entry stuck RUNNING for longer than this was abandoned by a process that
# died mid-refresh, not one still working.
STALE_RUNNING_MINUTES = 30

TRIGGER_NEW_PERIOD = "new_period"
TRIGGER_RESTATED = "restated_period"
TRIGGER_RECONCILIATION = "reconciliation"
TRIGGER_MANUAL = "manual"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def enqueue(entries: Iterable[dict[str, Any]], *, trigger: str = TRIGGER_NEW_PERIOD,
            force: bool = False,
            actor: str = "fundamentals_refresh") -> dict[str, Any]:
    """Add companies owed a refresh, without duplicating what is already owed.

    Keyed on company and period, so the same results announcement arriving twice
    - a feed replaying, a reconciliation pass overlapping a detector - produces
    one entry rather than two refreshes of identical work.

    An entry already SUCCESS for that period is left alone. Re-reporting the
    same quarter is not a reason to fetch it again; a restatement is, and says
    so through its own trigger.

    ``force`` overrides that, for a period that has to be collected again
    despite a prior success - a restatement, or a run whose success was recorded
    by code that has since been found wrong.
    """
    from institutional_warehouse import gateway, store

    wanted = [e for e in (entries or []) if e.get("symbol") and e.get("reporting_period")]
    if not wanted:
        return {"ok": True, "queued": 0, "skipped": 0}

    held = {(str(r.get("symbol")), str(r.get("reporting_period"))): r
            for r in store.all_rows(TAB, limit=20000) or []}

    rows: list[dict[str, Any]] = []
    skipped = 0
    for entry in wanted:
        symbol = str(entry["symbol"]).strip().upper()
        period = str(entry["reporting_period"]).strip()
        prior = held.get((symbol, period))
        if prior and not force:
            status = str(prior.get("status") or "")
            if status in (SUCCESS, RUNNING):
                skipped += 1
                continue
            if status == FAILED and int(prior.get("attempts") or 0) >= MAX_ATTEMPTS:
                skipped += 1
                continue
        rows.append({
            "symbol": symbol,
            "reporting_period": period,
            "status": PENDING,
            "trigger": entry.get("trigger") or trigger,
            "attempts": int((prior or {}).get("attempts") or 0),
            "queued_at": _now(),
            "last_error": None,
        })

    if not rows:
        return {"ok": True, "queued": 0, "skipped": skipped}
    out = gateway.write(TAB, rows, source=SOURCE, actor=actor, reason=f"enqueue:{trigger}")
    return {"ok": bool(out.get("ok")), "queued": len(rows), "skipped": skipped,
            "written": {k: out.get(k) for k in ("inserted", "updated", "unchanged")}}


def claim(limit: int = 25, *, actor: str = "fundamentals_refresh") -> list[dict[str, Any]]:
    """Take the next entries and mark them RUNNING.

    Marked before the work starts, so a process that dies mid-refresh leaves
    evidence rather than an entry that looks untouched and gets picked up again
    by every worker that follows.
    """
    from institutional_warehouse import gateway, store

    owed = [r for r in store.all_rows(TAB, limit=20000) or []
            if str(r.get("status") or "") in CLAIMABLE]
    owed.sort(key=lambda r: str(r.get("queued_at") or ""))
    taken = owed[:max(0, int(limit))]
    if not taken:
        return []
    gateway.write(TAB, [{"symbol": r["symbol"], "reporting_period": r["reporting_period"],
                         "status": RUNNING, "started_at": _now()} for r in taken],
                  source=SOURCE, actor=actor, reason="claim")
    return taken


UPDATED = "UPDATED"
NO_CHANGE = "NO_CHANGE"


def finish(symbol: str, period: str, *, ok: bool, error: Optional[str] = None,
           datasets: Optional[Iterable[str]] = None, periods_written: int = 0,
           periods_preserved: int = 0, attempts: Optional[int] = None,
           outcome: Optional[str] = None,
           actor: str = "fundamentals_refresh") -> dict[str, Any]:
    """Record how a refresh ended.

    A failure becomes RETRY until it has been tried enough times, then FAILED.
    The distinction matters to whoever is watching: RETRY is the system still
    working on it, FAILED is the system asking for help.
    """
    from institutional_warehouse import gateway, store

    symbol, period = str(symbol).strip().upper(), str(period).strip()
    prior = next((r for r in store.all_rows(TAB, limit=20000) or []
                  if str(r.get("symbol")) == symbol
                  and str(r.get("reporting_period")) == period), {})
    tries = int(attempts if attempts is not None else (prior.get("attempts") or 0)) + 1
    status = SUCCESS if ok else (RETRY if tries < MAX_ATTEMPTS else FAILED)
    row = {
        "symbol": symbol, "reporting_period": period, "status": status,
        "attempts": tries, "finished_at": _now(),
        "last_error": None if ok else str(error or "")[:400],
        "outcome": (outcome or (UPDATED if periods_written else NO_CHANGE)) if ok else None,
        "datasets_written": ",".join(sorted(datasets or [])) or None,
        "periods_written": int(periods_written),
        "periods_preserved": int(periods_preserved),
    }
    out = gateway.write(TAB, [row], source=SOURCE, actor=actor, reason=f"finish:{status}")
    return {"ok": bool(out.get("ok")), "status": status, "attempts": tries}


def recover_abandoned(*, minutes: int = STALE_RUNNING_MINUTES,
                      actor: str = "fundamentals_refresh") -> dict[str, Any]:
    """Return entries a dead process left RUNNING to the queue.

    Without this a deploy landing mid-refresh strands those companies forever:
    RUNNING is not claimable, and nothing else will ever change it.
    """
    from datetime import timedelta

    from institutional_warehouse import gateway, store

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    stranded = [r for r in store.all_rows(TAB, limit=20000) or []
                if str(r.get("status") or "") == RUNNING
                and str(r.get("started_at") or "") < cutoff]
    if not stranded:
        return {"ok": True, "recovered": 0}
    gateway.write(TAB, [{"symbol": r["symbol"], "reporting_period": r["reporting_period"],
                         "status": RETRY,
                         "last_error": "recovered: left running by a process that stopped"}
                        for r in stranded],
                  source=SOURCE, actor=actor, reason="recover_abandoned")
    return {"ok": True, "recovered": len(stranded),
            "symbols": [r["symbol"] for r in stranded][:25]}


def queue_state() -> dict[str, Any]:
    from institutional_warehouse import store

    rows = store.all_rows(TAB, limit=20000) or []
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("status") or "UNKNOWN")
        counts[key] = counts.get(key, 0) + 1
    blocked = [{"symbol": r.get("symbol"), "period": r.get("reporting_period"),
                "attempts": r.get("attempts"), "error": str(r.get("last_error") or "")[:160]}
               for r in rows if str(r.get("status")) == FAILED][:25]
    return {"ok": True, "total": len(rows), "by_status": counts,
            "owed": sum(counts.get(s, 0) for s in CLAIMABLE), "failed_sample": blocked}
