"""Backfill orchestration.

    scheduler → pending work → collector → validation → warehouse → checkpoint → continue

Every stage is resumable and budgeted. A run does a slice of the work and stops;
the next run picks up exactly where this one left off, because progress lives in
the checkpoint tables rather than in the process.
"""

from __future__ import annotations

import time

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, Optional

from institutional_warehouse import audit, store
from institutional_warehouse.backfill import (
    checkpoints, prices, prices_upstox, statements, valuation_history,
)
from institutional_warehouse.backfill.sources import nse_archive
from institutional_warehouse.values import now_iso

# upstox_prices precedes yahoo_prices deliberately. Yahoo silently downsamples
# a long range to monthly bars, which is how daily_market_history became a
# monthly series while every checkpoint read "done"; Upstox returns genuinely
# daily, already-adjusted candles back to 2000.
STAGES = ("nse_archive", "upstox_prices", "yahoo_prices", "yahoo_statements",
          "valuation_history")


def _truthy(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def worker_only() -> Optional[dict[str, Any]]:
    """A universe backfill is thousands of HTTP calls. It never runs inside Ask."""
    if _truthy("WAREHOUSE_BACKFILL_ALLOW_HERE"):
        return None
    role = (os.getenv("AGI_ROLE") or "").strip().lower()
    if role in ("gather_worker", "worker", "scheduler"):
        return None
    return {
        "ok": False,
        "error": "worker_only",
        "detail": (
            "Historical backfill runs on the gather worker. Set AGI_ROLE=gather_worker, "
            "or WAREHOUSE_BACKFILL_ALLOW_HERE=true to override deliberately."
        ),
        "role": role or "unset",
    }


def run_parallel(
    items: Iterable[str],
    worker: Callable[[str], dict[str, Any]],
    *,
    concurrency: int = 4,
) -> list[dict[str, Any]]:
    """Fan out per-company work. Kept modest: the sources rate-limit aggressively."""
    from observability import memory_stages as ms

    names = list(items)
    if not names:
        return []
    if concurrency <= 1:
        return [worker(name) for name in names]

    # Every company's full result is held here until the whole fan-out finishes.
    # If a result carries price history, vendor payloads or statement records,
    # 60 of them are alive at once by the end. Checkpointed every ten so the
    # shape is visible: flat means the results are small, linear means they are
    # not and the list is the problem.
    out: list[dict[str, Any]] = []
    stage_name = str(getattr(worker, "__name__", "") or "worker")
    ms.heartbeat("fanout_start", worker=stage_name, companies=len(names),
                 concurrency=int(concurrency))
    with ThreadPoolExecutor(max_workers=max(1, min(int(concurrency), 8))) as pool:
        futures = {pool.submit(worker, name): name for name in names}
        for future in as_completed(futures):
            try:
                out.append(future.result())
            except Exception as exc:
                out.append({"ok": False, "symbol": futures[future], "error": str(exc)[:200]})
            if len(out) % 10 == 0:
                ms.heartbeat("fanout_progress", worker=stage_name, completed=len(out),
                             of=len(names))
    ms.heartbeat("fanout_end", worker=stage_name, results=len(out))
    return out


def run(
    *,
    actor: str = "backfill",
    stages: Optional[Iterable[str]] = None,
    archive_start: Optional[str] = None,
    archive_floor: Optional[str] = None,
    companies: int = 25,
    days: int = 60,
    cadence: str = "monthly",
    universe: Optional[Iterable[str]] = None,
    fetch: Optional[Callable[[str], bytes]] = None,
    statement_loader: Optional[Callable[[str], dict[str, Any]]] = None,
    enforce_worker: bool = True,
    pause_seconds: float = 0.0,
    refresh_done: bool = False,
    deep_history: bool = False,
    max_seconds: Optional[float] = None,
) -> dict[str, Any]:
    """Run one slice of the historical backfill.

    ``refresh_done`` re-collects companies already marked complete. Needed after
    a fix that changes what a company's history contains rather than whether it
    could be fetched: the bhavcopy walker overwrote Upstox's split-adjusted
    prices with raw ones across 2022-12-27 to 2025-09-01, and those companies
    are all marked done.
    """
    if enforce_worker:
        blocked = worker_only()
        if blocked:
            return blocked

    wanted = [s for s in (stages or STAGES) if s in STAGES]
    job_id = checkpoints.start_job(
        "backfill",
        actor=actor,
        params={"stages": wanted, "companies": companies, "days": days,
                "cadence": cadence, "archive_start": archive_start,
                "archive_floor": archive_floor, "refresh_done": refresh_done},
    )
    started = now_iso()
    results: dict[str, Any] = {}
    errors: list[dict[str, str]] = []

    # A slice that can run forever is a slice that can stop the scheduler from
    # existing, because the first one runs on the boot path. Cooperative rather
    # than forced: a thread cannot be killed from outside in Python, so the
    # stages check it between companies and stop cleanly.
    deadline = (time.monotonic() + float(max_seconds)) if max_seconds else None

    runners: dict[str, Callable[[], dict[str, Any]]] = {
        "nse_archive": lambda: nse_archive.backfill(
            actor=actor, days=days, fetch=fetch,
            start=archive_start, floor=archive_floor),
        # days reaches this stage now. Without it the window defaulted to
        # EARLIEST and a twenty-day slice fetched from January 2000.
        "upstox_prices": lambda: prices_upstox.backfill(universe, actor=actor, limit=companies,
                                                        days=days, deep_history=deep_history,
                                                        pause_seconds=pause_seconds,
                                                        refresh_done=refresh_done,
                                                        deadline=deadline),
        "yahoo_prices": lambda: prices.backfill(universe, actor=actor, limit=companies,
                                                fetch=fetch, pause_seconds=pause_seconds),
        "yahoo_statements": lambda: statements.backfill(universe, actor=actor, limit=companies,
                                                        loader=statement_loader),
        "valuation_history": lambda: valuation_history.reconstruct(
            universe, actor=actor, limit=companies, cadence=cadence
        ),
    }

    # Measured per stage, because one of the five may dominate the payload and
    # a single number for the whole slice cannot say which.
    from observability import memory_stages as ms

    for stage in wanted:
        if deadline is not None and time.monotonic() > deadline:
            errors.append({"stage": stage, "error": "slice_deadline_reached"})
            results[stage] = {"ok": False, "stage": stage, "skipped": "deadline"}
            continue
        try:
            with ms.stage(f"backfill_stage_{stage}", companies=companies, days=days) as detail:
                results[stage] = runners[stage]()
                brief = results[stage] if isinstance(results[stage], dict) else {}
                detail["rows"] = brief.get("written") or brief.get("rows")
                detail["symbols"] = brief.get("symbols") or brief.get("companies")
            if results[stage].get("ok") is False:
                errors.append({"stage": stage, "error": str(results[stage].get("error"))})
        except Exception as exc:
            results[stage] = {"ok": False, "stage": stage, "error": str(exc)[:300]}
            errors.append({"stage": stage, "error": str(exc)[:300]})

    stats = {
        "stages": {k: _brief(v) for k, v in results.items()},
        "row_counts": {
            tab: store.row_count(tab)
            for tab in ("daily_market_history", "financials_annual", "financials_quarterly",
                        "historical_valuation", "corporate_actions")
        },
    }
    checkpoints.finish_job(job_id, ok=not errors, stats=stats,
                           error=errors[0]["error"] if errors else None)
    audit.record("refresh", actor=actor,
                 detail={"backfill_job": job_id, "stages": wanted, "errors": errors},
                 ok=not errors)

    return {
        "ok": not errors,
        "job_id": job_id,
        "started_at": started,
        "finished_at": now_iso(),
        "stages": results,
        "errors": errors,
        **stats,
    }


def _brief(payload: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "ok", "error", "days_imported", "rows_seen", "companies_done", "companies_failed",
        "rows_written", "annual_periods", "quarterly_periods", "observations", "queued",
        # Without this a failing stage reports only a count, and the cause has
        # to be guessed at from outside.
        "failure_reasons",
    )
    return {k: payload.get(k) for k in keep if k in payload}


def resume(*, actor: str = "backfill", **kwargs: Any) -> dict[str, Any]:
    """Alias that reads as what it does: continue the unfinished work."""
    return run(actor=actor, **kwargs)


def status() -> dict[str, Any]:
    return {
        "ok": True,
        "stages": list(STAGES),
        "dates": checkpoints.date_coverage(nse_archive.SOURCE),
        "entities": {
            kind: checkpoints.entity_coverage(kind)
            for kind in (prices.KIND, statements.KIND, valuation_history.KIND)
        },
        "recent_jobs": checkpoints.recent_jobs(limit=5),
        "failures": checkpoints.failures(limit=20),
        "worker_gate": worker_only() or {"ok": True, "allowed_here": True},
    }
