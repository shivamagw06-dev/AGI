"""Continuous HVIE universe bootstrap runtime — drains persisted queue until done."""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from historical_valuation_intelligence.models import ENGINE_CODE, VERSION
from historical_valuation_intelligence.universe_programme import aggregates, pipeline, queue
from historical_valuation_intelligence.universe_programme.models import (
    PROGRAMME_CODE,
    PROGRAMME_VERSION,
    QUEUE_PENDING,
    QUEUE_RETRY,
)

_LOCK = threading.Lock()
_THREAD: Optional[threading.Thread] = None
_STATE: dict[str, Any] = {
    "status": "idle",  # idle | running | stopped
    "started_at": None,
    "stopped": False,
    "last_tick": None,
    "last_error": None,
    "last_batch": None,
    "last_sync": None,
    "ticks": 0,
    "completed_this_session": 0,
    "failed_this_session": 0,
    "processed_this_session": 0,
    "started_mono": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truthy(name: str, default: str = "true") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def ensure_classified(
    *,
    recover_running: bool = True,
    adopt_existing: bool = True,
) -> dict[str, Any]:
    out = queue.sync_universe(
        recover_running=recover_running,
        adopt_existing=adopt_existing,
    )
    with _LOCK:
        _STATE["last_sync"] = _now()
    return out


def process_batch(*, batch: int = 3, sync: bool = False) -> dict[str, Any]:
    """Claim and process one batch from the persisted queue."""
    sync_out = None
    if sync:
        # Light sync while running: no RUNNING recovery, no full HVIE import.
        sync_out = ensure_classified(recover_running=False, adopt_existing=False)
        pipeline.requeue_waiting(limit=40)

    claimed = queue.next_batch(batch=batch)
    results = []
    ok = 0
    failed = 0
    skipped = 0
    completed = 0
    t0 = time.time()
    for row in claimed:
        sym = str(row.get("symbol") or "").upper()
        try:
            out = pipeline.process_company(sym)
        except Exception as exc:
            out = {"ok": False, "symbol": sym, "error": str(exc)[:200], "queue_status": "RETRY"}
            queue.upsert_queue_row(
                sym,
                queue_status=QUEUE_RETRY,
                lifecycle="READY",
                last_error=str(exc)[:280],
                next_retry_at=_now(),
            )
        results.append(out)
        status = str(out.get("queue_status") or "").upper()
        if out.get("ok") and status == "COMPLETED":
            completed += 1
            ok += 1
        elif status == "SKIPPED":
            skipped += 1
            ok += 1
        elif status == "FAILED":
            failed += 1
        elif status == "RETRY":
            failed += 1
        else:
            ok += 1

    elapsed = max(0.001, time.time() - t0)
    counts = queue.pipeline_counts()
    with _LOCK:
        _STATE["last_tick"] = _now()
        _STATE["ticks"] = int(_STATE.get("ticks") or 0) + 1
        _STATE["last_batch"] = {
            "attempted": len(claimed),
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "elapsed_seconds": round(elapsed, 2),
        }
        _STATE["completed_this_session"] += completed
        _STATE["failed_this_session"] += failed
        _STATE["processed_this_session"] += len(claimed)

    return {
        "ok": True,
        "mode": "universe_bootstrap",
        "attempted": len(claimed),
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "elapsed_seconds": round(elapsed, 2),
        "companies_per_hour": round(len(claimed) * 3600.0 / elapsed, 1) if claimed else 0.0,
        "pipeline": counts,
        "sync": sync_out,
        "engine": ENGINE_CODE,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
        "results": results,
    }


def throughput() -> dict[str, Any]:
    counts = queue.pipeline_counts()
    with _LOCK:
        processed = int(_STATE.get("processed_this_session") or 0)
        started = _STATE.get("started_mono")
        session_completed = int(_STATE.get("completed_this_session") or 0)
    elapsed_h = 0.0
    if started:
        elapsed_h = max(0.001, (time.time() - float(started)) / 3600.0)
    speed = (processed / elapsed_h) if started and processed else 0.0
    remaining = int(counts.get("pending") or 0) + int(counts.get("retry") or 0) + int(counts.get("running") or 0)
    eta_hours = (remaining / speed) if speed > 0 else None
    return {
        "ok": True,
        "universe": counts.get("universe"),
        "completed": counts.get("complete"),
        "remaining": remaining,
        "speed_per_hour": round(speed, 1),
        "eta_hours": round(eta_hours, 1) if eta_hours is not None else None,
        "session_processed": processed,
        "session_completed": session_completed,
        "pipeline": counts,
    }


def _plain_english(pipe: dict[str, Any], runtime_status: str, thr: dict[str, Any]) -> str:
    universe = int(pipe.get("universe") or 0)
    complete = int(pipe.get("complete") or 0)
    pending = int(pipe.get("pending") or 0)
    retry = int(pipe.get("retry") or 0)
    failed = int(pipe.get("failed") or 0)
    skipped = int(pipe.get("skipped") or 0)
    running = int(pipe.get("running") or 0)
    pct = round(100.0 * complete / universe, 1) if universe else 0.0

    if universe <= 0:
        return "No companies loaded yet. Press Start — we will build the work list from the warehouse."
    if complete >= universe and pending == 0 and retry == 0 and running == 0:
        return f"Done. Historical valuation is ready for all {universe} companies."
    if runtime_status == "running":
        eta = thr.get("eta_hours")
        eta_bit = f" About {eta} hours left at the current speed." if eta is not None else ""
        return (
            f"Working now: {complete} of {universe} finished ({pct}%). "
            f"{pending + retry} still waiting, {running} in progress, {skipped} waiting on missing data."
            f"{eta_bit}"
        )
    if failed and pending == 0 and retry == 0 and running == 0:
        return f"{complete} finished, {failed} failed. Press Resume to retry failures, or Start to continue."
    return (
        f"{complete} of {universe} companies finished ({pct}%). "
        f"Press Start to keep building historical PE/PB/EV for the rest."
    )


def status() -> dict[str, Any]:
    with _LOCK:
        snap = {k: v for k, v in _STATE.items() if k != "started_mono"}
    pipe = queue.pipeline_counts()
    qcounts = queue.queue_counts()
    thr = throughput()
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
        "hvie_version": VERSION,
        "runtime": snap,
        "queue": qcounts,
        "pipeline": pipe,
        "throughput": thr,
        "plain_english": _plain_english(pipe, str(snap.get("status") or "idle"), thr),
        "completion": {
            "pending": pipe.get("pending"),
            "running": pipe.get("running"),
            "retry": pipe.get("retry"),
            "done": (
                int(pipe.get("pending") or 0) == 0
                and int(pipe.get("running") or 0) == 0
                and int(pipe.get("retry") or 0) == 0
            ),
        },
        "schedules": {
            "bootstrap": "continuous until pending=running=retry=0",
            "daily": "append one observation after bootstrap complete",
            "statement": "forward reconstruct release→today",
            "corporate_action": "full reconstruct on structural CA",
        },
    }


def board() -> dict[str, Any]:
    """Single payload for the admin UI — avoids 4 heavy parallel polls."""
    with _LOCK:
        snap = {k: v for k, v in _STATE.items() if k != "started_mono"}
    pipe = queue.pipeline_counts()
    thr = throughput()
    runtime_status = str(snap.get("status") or "idle")
    universe = int(pipe.get("universe") or 0)
    complete = int(pipe.get("complete") or 0)
    pct = round(100.0 * complete / universe, 1) if universe else 0.0
    lists = queue.board_rows(limit_fail=20, limit_next=12)
    life = queue.lifecycle_counts()
    stages = [
        {"name": "All companies", "count": pipe.get("universe"), "hint": "Full listed universe on the queue"},
        {"name": "Have enough data", "count": pipe.get("eligible"), "hint": "Prices + statements + share count"},
        {"name": "History built", "count": pipe.get("seeded_history"), "hint": "Reconstructed from statements + prices"},
        {"name": "Statistics", "count": pipe.get("statistics"), "hint": "Means / medians / bands inputs"},
        {"name": "Percentile ready", "count": pipe.get("percentiles"), "hint": "Where valuation sits vs history"},
        {"name": "Regime ready", "count": pipe.get("regimes"), "hint": "Cheap / fair / expensive label"},
        {"name": "Finished", "count": pipe.get("complete"), "hint": "Fully usable for research"},
    ]
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
        "reconstruction_version": "8.3B",
        "vendor_historical_ratios": False,
        "runtime": {
            "status": runtime_status,
            "started_at": snap.get("started_at"),
            "last_tick": snap.get("last_tick"),
            "last_error": snap.get("last_error"),
            "last_batch": snap.get("last_batch"),
            "completed_this_session": snap.get("completed_this_session"),
            "failed_this_session": snap.get("failed_this_session"),
            "processed_this_session": snap.get("processed_this_session"),
        },
        "progress": {
            "universe": universe,
            "complete": complete,
            "percent": pct,
            "pending": pipe.get("pending"),
            "running": pipe.get("running"),
            "retry": pipe.get("retry"),
            "failed": pipe.get("failed"),
            "skipped": pipe.get("skipped"),
            "waiting_prices": life.get("WAITING_PRICE_HISTORY", 0),
            "waiting_statements": life.get("WAITING_STATEMENTS", 0),
            "waiting_corporate_actions": life.get("WAITING_CORPORATE_ACTIONS", 0),
            "waiting_share_count": life.get("WAITING_SHARE_COUNT", 0),
            "ready": life.get("READY", 0),
        },
        "pipeline": pipe,
        "stages": stages,
        "throughput": {
            "speed_per_hour": thr.get("speed_per_hour"),
            "eta_hours": thr.get("eta_hours"),
            "remaining": thr.get("remaining"),
            "session_completed": thr.get("session_completed"),
        },
        "plain_english": _plain_english(pipe, runtime_status, thr),
        "failures": lists.get("failures") or [],
        "next_up": lists.get("next_up") or [],
        "recent_complete": lists.get("recent_complete") or [],
        "what_this_does": (
            "Builds historical PE, PB, EV, EV/EBITDA, EV/Sales and profitability from "
            "warehouse prices + normalized financial statements + corporate actions "
            "(Phase 8.3B). It never downloads vendor historical ratios. "
            "Press Start and leave it running — progress is saved if the server restarts."
        ),
        "lifecycle": life,
        "buttons": {
            "start": "Start / keep the background worker running until the queue is empty.",
            "stop": "Pause the background worker. Progress already saved stays saved.",
            "resume": "Reload the work list (including older HVIE progress) and start again.",
            "run_batch": "Process a small batch once, without leaving the worker on.",
        },
    }


def pipeline_dashboard() -> dict[str, Any]:
    pipe = queue.pipeline_counts()
    return {
        "ok": True,
        "title": "HVIE Pipeline",
        "stages": [
            {"name": "Universe", "count": pipe.get("universe"), "pct": 100.0},
            {"name": "Eligible", "count": pipe.get("eligible")},
            {"name": "Seeded / History Built", "count": pipe.get("seeded_history")},
            {"name": "Statistics", "count": pipe.get("statistics")},
            {"name": "Percentiles", "count": pipe.get("percentiles")},
            {"name": "Bands", "count": pipe.get("bands")},
            {"name": "Regimes", "count": pipe.get("regimes")},
            {"name": "Research Timeline", "count": pipe.get("research")},
            {"name": "Complete", "count": pipe.get("complete")},
        ],
        "queue": queue.queue_counts(),
        "lifecycle": queue.lifecycle_counts(),
        "throughput": throughput(),
        "engine": ENGINE_CODE,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def failures(*, limit: int = 100) -> dict[str, Any]:
    rows = [
        r for r in queue.all_queue_rows()
        if str(r.get("queue_status") or "").upper() in {"FAILED", "RETRY", "SKIPPED"}
    ]
    rows.sort(key=lambda r: str(r.get("last_run_at") or ""), reverse=True)
    return {
        "ok": True,
        "count": len(rows),
        "rows": rows[: max(1, min(int(limit), 500))],
    }


def company_status(symbol: str) -> dict[str, Any]:
    row = queue.get_queue_row(symbol)
    return {
        "ok": bool(row),
        "symbol": str(symbol or "").upper(),
        "row": row or None,
        "engine": ENGINE_CODE,
        "programme": PROGRAMME_CODE,
    }


def retry_symbol(symbol: str) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    queue.upsert_queue_row(
        ticker,
        queue_status=QUEUE_PENDING,
        lifecycle="READY",
        next_retry_at=None,
        last_error=None,
        reason="manual_retry",
    )
    out = pipeline.process_company(ticker)
    return {"ok": True, "result": out}


def reconstruct_symbol(symbol: str) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    queue.upsert_queue_row(
        ticker,
        queue_status=QUEUE_PENDING,
        lifecycle="READY",
        attempts=0,
        next_retry_at=None,
        last_error=None,
        reason="manual_reconstruct",
    )
    return pipeline.process_company(ticker)


def persist_aggregates(*, metric: str = "pe") -> dict[str, Any]:
    return aggregates.persist_cross_section_medians(metric=metric)


def start(*, interval_seconds: Optional[float] = None, batch: Optional[int] = None) -> dict[str, Any]:
    global _THREAD
    if not _truthy("HVIE_UNIVERSE_RUNTIME", "true"):
        return {"ok": True, "enabled": False, "reason": "HVIE_UNIVERSE_RUNTIME=false"}
    if _THREAD and _THREAD.is_alive():
        with _LOCK:
            snap = {k: v for k, v in _STATE.items() if k != "started_mono"}
        return {
            "ok": True,
            "enabled": True,
            "already_running": True,
            "runtime": snap,
            "programme": PROGRAMME_CODE,
        }

    # Smaller batches + longer pause: each company reconstruct is heavy; large
    # batches were 502'ing the Render service when Start + UI polls stacked.
    interval = float(interval_seconds or os.getenv("HVIE_UNIVERSE_INTERVAL_SECONDS") or 120)
    batch_n = int(batch or os.getenv("HVIE_UNIVERSE_BATCH") or 3)
    sync_every = max(1, int(os.getenv("HVIE_UNIVERSE_SYNC_EVERY_TICKS") or 8))

    def _loop() -> None:
        with _LOCK:
            _STATE["status"] = "running"
            _STATE["started_at"] = _now()
            _STATE["started_mono"] = time.time()
            _STATE["stopped"] = False
            _STATE["ticks"] = 0
            _STATE["last_error"] = None
            _STATE["completed_this_session"] = 0
            _STATE["failed_this_session"] = 0
            _STATE["processed_this_session"] = 0
        try:
            ensure_classified(recover_running=True)
        except Exception as exc:
            with _LOCK:
                _STATE["last_error"] = f"sync_failed:{exc}"[:300]
        while True:
            with _LOCK:
                if _STATE.get("stopped"):
                    break
                ticks = int(_STATE.get("ticks") or 0)
            try:
                out = process_batch(batch=batch_n, sync=(ticks > 0 and ticks % sync_every == 0))
                done = (
                    int((out.get("pipeline") or {}).get("pending") or 0) == 0
                    and int((out.get("pipeline") or {}).get("retry") or 0) == 0
                    and int((out.get("pipeline") or {}).get("running") or 0) == 0
                )
                if done:
                    try:
                        persist_aggregates(metric="pe")
                    except Exception:
                        pass
                    try:
                        pipeline.requeue_waiting(limit=100)
                    except Exception:
                        pass
                    time.sleep(max(90.0, interval))
                    continue
            except Exception as exc:
                with _LOCK:
                    _STATE["last_error"] = str(exc)[:300]
            time.sleep(max(30.0, interval))
        with _LOCK:
            _STATE["status"] = "stopped"

    _THREAD = threading.Thread(target=_loop, name="hvie-universe-runtime", daemon=True)
    _THREAD.start()
    return {
        "ok": True,
        "enabled": True,
        "interval_seconds": interval,
        "batch": batch_n,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def stop() -> dict[str, Any]:
    with _LOCK:
        _STATE["stopped"] = True
        _STATE["status"] = "stopped"
    return {"ok": True, "stopped": True}


def resume() -> dict[str, Any]:
    """Reload queue (adopt classic HVIE progress) and start the worker."""
    ensure_classified(recover_running=True)
    return start()
