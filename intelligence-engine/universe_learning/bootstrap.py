"""Seed the historical-depth queue and start Continuous Gather → Learn.

Scopes:
  nifty500  — index books through Nifty 500 (default institutional depth)
  indices   — all loaded market_indices CSVs
  all       — full NSE trading book (EQUITY_L / NIFTYstocks) ∪ indices
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any

UNIVERSE_LEARNING_VERSION = "universe-learning-v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _scope_symbols(scope: str) -> list[str]:
    from knowledge_factory.historical_depth import universe_priority as up

    s = (scope or "nifty500").strip().lower()
    if s in {"all", "nse", "equity", "trading", "equity_l"}:
        return up.supported_universe()
    if s in {"indices", "index", "market_indices"}:
        return list(
            dict.fromkeys(
                [
                    *up.nifty_50(),
                    *up.nifty_next_50(),
                    *up.nifty_100(),
                    *up.nifty_200(),
                    *up.nifty_500(),
                    *up.nifty_midcap_select(),
                    *up.nifty_bank(),
                    *up.nifty_financial_services(),
                ]
            )
        )
    # default / nifty500
    return list(
        dict.fromkeys(
            [
                *up.nifty_50(),
                *up.nifty_next_50(),
                *up.nifty_100(),
                *up.nifty_200(),
                *up.nifty_500(),
            ]
        )
    )


def learning_status() -> dict[str, Any]:
    from knowledge_factory.historical_depth import universe_priority as up

    summary = up.universe_summary()
    queue_meta: dict[str, Any] = {}
    progress: dict[str, Any] = {}
    cgl: dict[str, Any] = {}
    try:
        from knowledge_factory.historical_depth import queue as bf_queue

        q = bf_queue.load_queue()
        queue_meta = {
            "queue_length": q.get("queue_length"),
            "completed_count": q.get("completed_count"),
            "companies": len(q.get("companies") or []),
            "updated_at": q.get("updated_at"),
        }
    except Exception as exc:
        queue_meta = {"error": str(exc)[:160]}
    try:
        from knowledge_factory.historical_depth.backfill import coverage_progress

        progress = coverage_progress()
    except Exception as exc:
        progress = {"error": str(exc)[:160]}
    try:
        from continuous_gather_learn.production import health as cgl_health

        cgl = cgl_health()
    except Exception as exc:
        cgl = {"error": str(exc)[:160]}
    return {
        "ok": True,
        "version": UNIVERSE_LEARNING_VERSION,
        "generated_at": _now(),
        "universe": summary,
        "queue": queue_meta,
        "progress": progress,
        "cgl": {
            "enabled": cgl.get("enabled"),
            "flags": cgl.get("flags"),
            "store_root": cgl.get("store_root"),
            "background": cgl.get("background"),
        },
        "mission": (
            "Gather filings, financials, evidence and structured knowledge for every "
            "company in the selected universe — Continuous Gather → Learn, without "
            "user interaction per ticker."
        ),
    }


def _run_cgl_async(*, slot: str) -> dict[str, Any]:
    """Fire-and-forget overnight/historical cycle so the API returns quickly."""

    def _worker() -> None:
        try:
            from continuous_gather_learn.orchestrator import run_cycle

            run_cycle(slot=slot, include_faa=True)
        except Exception:
            pass

    # Under pytest, stay synchronous stub — do not start long cycles
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("IO_ALLOW_LIVE_IN_PYTEST") != "1":
        return {"ok": True, "status": "pytest_stub", "slot": slot}

    threading.Thread(target=_worker, name=f"universe-learn-{slot}", daemon=True).start()
    return {"ok": True, "status": "queued", "slot": slot}


def bootstrap_universe_learning(
    *,
    scope: str = "nifty500",
    run_cgl: bool = True,
    slot: str = "overnight",
    force_refresh_queue: bool = True,
    icf_tick: bool = False,
) -> dict[str, Any]:
    """Ensure HD queue covers the scope and optionally start CGL gathering."""
    symbols = _scope_symbols(scope)
    from knowledge_factory.historical_depth import queue as bf_queue
    from knowledge_factory.historical_depth import universe_priority as up

    # Seed / refresh the persistent backlog for the full supported book,
    # then report how many of the scoped symbols are pending.
    queue_body = bf_queue.ensure_queue(force_refresh=force_refresh_queue)
    # Explicitly enqueue scoped symbols (reopens completed ones if force)
    enqueued = 0
    if force_refresh_queue:
        for sym in symbols:
            bf_queue.enqueue_company(sym, reason=f"universe_learning:{scope}")
            enqueued += 1
        queue_body = bf_queue.load_queue()

    pending = [
        c
        for c in (queue_body.get("companies") or [])
        if str(c.get("status")) in {"pending", "running", "failed", "cooldown"}
        and str(c.get("company") or "").upper() in set(symbols)
    ]

    # Onboard every scoped company into the Institutional Knowledge Tables
    # master registry (real universe fields; cheap — CSV reads + JSON writes).
    # Under pytest, run synchronously and small so assertions are deterministic;
    # in production this can be thousands of file writes, so run off-thread.
    ikt_onboard: dict[str, Any] = {"ok": False, "skipped": True}
    try:
        from institutional_knowledge_tables.sync import sync_universe_company_master

        if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("IO_ALLOW_LIVE_IN_PYTEST") != "1":
            ikt_onboard = sync_universe_company_master(scope=scope, limit=25)
        else:

            def _onboard_worker() -> None:
                try:
                    sync_universe_company_master(scope=scope)
                except Exception:
                    pass

            threading.Thread(
                target=_onboard_worker, name=f"ikt-onboard-{scope}", daemon=True
            ).start()
            ikt_onboard = {"ok": True, "status": "queued", "scope": scope}
    except Exception as exc:
        ikt_onboard = {"ok": False, "error": str(exc)[:200]}

    cgl_job: dict[str, Any] = {"ok": False, "skipped": True}
    if run_cgl:
        cgl_job = _run_cgl_async(slot=slot)

    icf_result: dict[str, Any] = {"ok": False, "skipped": True}
    if icf_tick:
        try:
            from institutional_coverage_factory.production import run_coverage_tick

            icf_scope = "UNIVERSE" if scope in {"nifty500", "indices"} else "UNIVERSE"
            icf_result = {
                "ok": True,
                "result": run_coverage_tick(scope=icf_scope, dispatch=True, limit=8),
            }
        except Exception as exc:
            icf_result = {"ok": False, "error": str(exc)[:200]}

    return {
        "ok": True,
        "version": UNIVERSE_LEARNING_VERSION,
        "generated_at": _now(),
        "scope": scope,
        "scoped_symbols": len(symbols),
        "sample": symbols[:15],
        "universe": up.universe_summary(),
        "queue": {
            "total_companies": len(queue_body.get("companies") or []),
            "queue_length": queue_body.get("queue_length"),
            "completed_count": queue_body.get("completed_count"),
            "scoped_pending": len(pending),
            "explicitly_enqueued": enqueued,
        },
        "cgl": cgl_job,
        "icf": icf_result,
        "ikt_onboard": ikt_onboard,
        "message": (
            f"Learning queue ready for {len(symbols)} companies (scope={scope}). "
            "CGL gathers filings/financials/evidence in priority order: "
            "Nifty 50 → Next 50 → 100 → 200 → 500 → residual NSE."
        ),
        "next": [
            "GET /v1/universe-learning/status",
            "GET /v1/continuous-gather-learn/dashboard",
            "GET /v1/knowledge-factory/historical-depth",
        ],
    }
