"""Daily refresh scheduler.

The warehouse refreshes once a day after the Indian market close and the
bhavcopy publication — 18:45 IST by default. The thread is deliberately dumb:
it wakes every minute, checks whether the daily slot has passed and whether
today's run has already happened, and calls the pipeline.

Enable with ``WAREHOUSE_DAILY_REFRESH=true``; change the slot with
``WAREHOUSE_REFRESH_AT`` (24h IST, e.g. ``18:45``).
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

IST = timezone(timedelta(hours=5, minutes=30))

_THREAD: Optional[threading.Thread] = None
_STOP = threading.Event()
_STATE: dict[str, Any] = {"last_run_date": None, "last_result": None, "runs": 0}


def _truthy(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def refresh_slot() -> tuple[int, int]:
    raw = (os.getenv("WAREHOUSE_REFRESH_AT") or "18:45").strip()
    try:
        hour, minute = raw.split(":")
        return max(0, min(int(hour), 23)), max(0, min(int(minute), 59))
    except Exception:
        return 18, 45


def due(now: Optional[datetime] = None) -> bool:
    moment = (now or datetime.now(timezone.utc)).astimezone(IST)
    hour, minute = refresh_slot()
    if (moment.hour, moment.minute) < (hour, minute):
        return False
    return _STATE.get("last_run_date") != moment.date().isoformat()


def run_once(*, actor: str = "scheduler", days: int = 10) -> dict[str, Any]:
    from institutional_warehouse.refresh import run

    result = run(actor=actor, days=days)
    _STATE["last_run_date"] = datetime.now(IST).date().isoformat()
    _STATE["last_result"] = {
        "run_id": result.get("run_id"),
        "ok": result.get("ok"),
        "finished_at": result.get("finished_at"),
        "errors": result.get("errors"),
    }
    _STATE["runs"] = int(_STATE.get("runs") or 0) + 1
    return result


def _loop(poll_seconds: float) -> None:
    while not _STOP.wait(poll_seconds):
        try:
            if due():
                run_once()
        except Exception:
            # A failed refresh must never kill the scheduler; the run record and
            # the audit trail carry the error.
            continue


def start(*, boot_run: bool = False, poll_seconds: float = 60.0) -> dict[str, Any]:
    from observability import memory_stages as ms

    global _THREAD
    ms.heartbeat("warehouse_scheduler_entered")
    if not _truthy("WAREHOUSE_DAILY_REFRESH"):
        return {"ok": True, "enabled": False, "reason": "WAREHOUSE_DAILY_REFRESH is off"}
    if _THREAD and _THREAD.is_alive():
        return {"ok": True, "enabled": True, "already_running": True}

    hour, minute = refresh_slot()
    if boot_run:
        try:
            run_once(actor="scheduler_boot")
        except Exception:
            pass

    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, args=(poll_seconds,), name="warehouse-refresh",
                               daemon=True)
    _THREAD.start()
    ms.heartbeat("warehouse_scheduler_ready")
    return {"ok": True, "enabled": True, "slot_ist": f"{hour:02d}:{minute:02d}", "boot_run": boot_run}


def stop() -> dict[str, Any]:
    _STOP.set()
    thread = _THREAD
    if thread and thread.is_alive():
        thread.join(timeout=5.0)
    return {"ok": True, "stopped": True}


def status() -> dict[str, Any]:
    hour, minute = refresh_slot()
    return {
        "ok": True,
        "enabled": _truthy("WAREHOUSE_DAILY_REFRESH"),
        "running": bool(_THREAD and _THREAD.is_alive()),
        "slot_ist": f"{hour:02d}:{minute:02d}",
        "due_now": due(),
        "backfill": backfill_status(),
        **_STATE,
    }


# --------------------------------------------------------------------------
# Continuous historical backfill
# --------------------------------------------------------------------------

_BACKFILL_THREAD: Optional[threading.Thread] = None
_BACKFILL_STOP = threading.Event()
_BACKFILL_STATE: dict[str, Any] = {"slices": 0, "last_slice_at": None, "last_result": None}


def _backfill_slice() -> dict[str, Any]:
    from institutional_warehouse.backfill.engine import run

    if within_market_hours():
        _BACKFILL_STATE["last_skip_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return {"ok": True, "skipped": "market_hours"}

    companies = int(os.getenv("WAREHOUSE_BACKFILL_COMPANIES", "25") or 25)
    days = int(os.getenv("WAREHOUSE_BACKFILL_DAYS", "40") or 40)
    result = run(actor="backfill_scheduler", companies=companies, days=days)
    _BACKFILL_STATE["slices"] = int(_BACKFILL_STATE.get("slices") or 0) + 1
    _BACKFILL_STATE["last_slice_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _BACKFILL_STATE["last_result"] = {
        "ok": result.get("ok"),
        "job_id": result.get("job_id"),
        "stages": result.get("stages", {}).keys() and list(result.get("stages", {})),
        "errors": result.get("errors"),
    }
    return result


# NSE trades 09:15 to 15:30 IST. The backfill is held off during those hours,
# plus a margin either side for the pre-open and the closing auction.
#
# Not a courtesy - a necessity. The desk rebuilds its cache every fifteen
# minutes, and that rebuild takes about twelve seconds on an idle box. With a
# backfill slice running it goes past sixty and the request times out. On
# 21 August that was happening at 11:48 IST with the market open.
#
# The repair has all night. The client looking at a screen does not.
MARKET_OPEN_IST = (9, 0)
MARKET_CLOSE_IST = (15, 45)


def maintenance_window_open(now: Optional[datetime] = None) -> bool:
    """Whether a declared maintenance window is still running.

    Set WAREHOUSE_MAINTENANCE_UNTIL to a date (YYYY-MM-DD) and the market guard
    stands down until it passes. It carries its own expiry on purpose: a boolean
    override is switched on for a quiet week and is still on months later, the
    first time it costs somebody a trading day.

    An unparseable value means no window. Failing closed here just means the
    guard stays on, which is the safe direction.
    """
    raw = (os.getenv("WAREHOUSE_MAINTENANCE_UNTIL") or "").strip()
    if not raw:
        return False
    try:
        until = datetime.fromisoformat(raw).date()
    except ValueError:
        return False
    return (now or datetime.now(timezone.utc)).astimezone(IST).date() <= until


def within_market_hours(now: Optional[datetime] = None) -> bool:
    """True while the exchange is trading, so heavy work can stand aside."""
    if not _truthy("WAREHOUSE_BACKFILL_MARKET_GUARD", "true"):
        return False
    if maintenance_window_open(now):
        return False
    moment = (now or datetime.now(timezone.utc)).astimezone(IST)
    if moment.weekday() >= 5:  # the exchange is shut at the weekend
        return False
    minutes = moment.hour * 60 + moment.minute
    start = MARKET_OPEN_IST[0] * 60 + MARKET_OPEN_IST[1]
    end = MARKET_CLOSE_IST[0] * 60 + MARKET_CLOSE_IST[1]
    return start <= minutes < end


def _backfill_loop(interval_seconds: float) -> None:
    from observability import memory_stages as ms

    while not _BACKFILL_STOP.wait(interval_seconds):
        try:
            with ms.stage("warehouse_backfill_slice",
                          companies=os.getenv("WAREHOUSE_BACKFILL_COMPANIES"),
                          days=os.getenv("WAREHOUSE_BACKFILL_DAYS")) as detail:
                result = _backfill_slice()
                if isinstance(result, dict):
                    detail["rows"] = result.get("written") or result.get("rows")
                    detail["symbols"] = result.get("symbols") or result.get("companies")
        except Exception:
            # A bad slice is recorded in the job table; the loop keeps going so a
            # single unreachable source cannot end the backfill.
            continue


def minutes_since_last_slice() -> Optional[float]:
    """Age of the last recorded slice, from the database rather than this process.

    The timer lives in memory, so every redeploy resets it. The job table does
    not, which is what lets a restarted process tell whether work is overdue.
    """
    try:
        from institutional_warehouse.backfill.checkpoints import recent_jobs

        jobs = recent_jobs(limit=1)
        if not jobs:
            return None
        stamp = datetime.fromisoformat(str(jobs[0].get("created_at")))
        return (datetime.now(timezone.utc) - stamp).total_seconds() / 60.0
    except Exception:
        return None


def start_backfill(*, boot_slice: Optional[bool] = None) -> dict[str, Any]:
    """Run a bounded backfill slice on a timer until the history is deep enough.

    The boot slice below runs *synchronously*, before the timer thread exists,
    and the caller only logs `gather_worker_warehouse_backfill` once this
    returns. So a slow boot slice makes the sidecar look hung with no log line
    naming the stage it is in - which is precisely what it did on 21 August,
    silent for 25 minutes after `gather_worker_warehouse`.
    """
    from observability import memory_stages as ms

    global _BACKFILL_THREAD
    ms.heartbeat("backfill_entered")
    if not _truthy("WAREHOUSE_BACKFILL"):
        ms.heartbeat("backfill_disabled")
        return {"ok": True, "enabled": False, "reason": "WAREHOUSE_BACKFILL is off"}
    if _BACKFILL_THREAD and _BACKFILL_THREAD.is_alive():
        return {"ok": True, "enabled": True, "already_running": True}

    minutes = float(os.getenv("WAREHOUSE_BACKFILL_INTERVAL_MIN", "30") or 30)

    # A redeploy restarts this process and, with a purely in-memory timer, would
    # idle a full interval before doing any work. Decide from the job table
    # instead: if a slice is already overdue, run one now; if one just ran, wait.
    age = minutes_since_last_slice()
    if boot_slice is None:
        boot_slice = age is None or age >= minutes
    if boot_slice and within_market_hours():
        boot_slice = False
    if boot_slice:
        ms.heartbeat("backfill_boot_slice_start",
                     companies=os.getenv("WAREHOUSE_BACKFILL_COMPANIES"),
                     days=os.getenv("WAREHOUSE_BACKFILL_DAYS"))
        try:
            with ms.stage("warehouse_backfill_boot_slice",
                          companies=os.getenv("WAREHOUSE_BACKFILL_COMPANIES"),
                          days=os.getenv("WAREHOUSE_BACKFILL_DAYS")) as detail:
                result = _backfill_slice()
                if isinstance(result, dict):
                    detail["rows"] = result.get("written") or result.get("rows")
                    detail["symbols"] = result.get("symbols") or result.get("companies")
        except Exception:
            pass
        ms.heartbeat("backfill_boot_slice_end")

    _BACKFILL_STOP.clear()
    _BACKFILL_THREAD = threading.Thread(target=_backfill_loop, args=(minutes * 60.0,),
                                        name="warehouse-backfill", daemon=True)
    _BACKFILL_THREAD.start()
    ms.heartbeat("backfill_timer_started", interval_minutes=minutes)
    return {"ok": True, "enabled": True, "interval_minutes": minutes, "boot_slice": boot_slice,
            "minutes_since_last_slice": round(age, 1) if age is not None else None}


def stop_backfill() -> dict[str, Any]:
    _BACKFILL_STOP.set()
    thread = _BACKFILL_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=5.0)
    return {"ok": True, "stopped": True}


def backfill_status() -> dict[str, Any]:
    age = minutes_since_last_slice()
    return {
        "enabled": _truthy("WAREHOUSE_BACKFILL"),
        "running_in_this_process": bool(_BACKFILL_THREAD and _BACKFILL_THREAD.is_alive()),
        # The loop runs in the gather worker, so a web process asking this
        # question must answer from the shared job table, not its own thread.
        "minutes_since_last_slice": round(age, 1) if age is not None else None,
        "loop_healthy": age is not None
        and age < float(os.getenv("WAREHOUSE_BACKFILL_INTERVAL_MIN", "30") or 30) * 2.5,
        "interval_minutes": float(os.getenv("WAREHOUSE_BACKFILL_INTERVAL_MIN", "30") or 30),
        "companies_per_slice": int(os.getenv("WAREHOUSE_BACKFILL_COMPANIES", "25") or 25),
        "days_per_slice": int(os.getenv("WAREHOUSE_BACKFILL_DAYS", "40") or 40),
        **_BACKFILL_STATE,
    }
