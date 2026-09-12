"""Runs the options-lab collector inside the API server process.

The lab was fully built and collecting nothing. render.yaml gave it a database
path, a report directory and OPTIONS_LAB_LIVE_VALIDATION=true, but no deployed
service ran options_lab.automation.run_worker, and nothing read that flag, so
every table behind the validation dashboard stayed empty.

The collector does not need a process of its own. It sleeps almost all day,
wakes once per 15-minute bucket during the NSE session, and needs the Upstox
token and the /var/data disk -- all of which the engine already has. So it runs
here, on a service that is already deployed and always on, instead of waiting
for a fifth Render worker that nobody had created.

This is not run_worker: that installs SIGTERM and SIGINT handlers, which is
right for a standalone process and wrong inside the API server, where it would
take over the engine's own shutdown. The loop body is shared via worker_tick;
only the stopping and the signal handling differ.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger

from .automation import WorkerState, worker_tick
from .upstox_live import LiveConfig

log = get_logger(__name__)

# One 15-minute bucket is the collection unit, so a minute of granularity is
# ample. Short enough that a restart mid-session resumes promptly.
POLL_SECONDS = 60

_state = WorkerState()
_thread: threading.Thread | None = None
_stop = threading.Event()
_disabled_reason: str | None = None


def enabled() -> bool:
    return os.getenv("OPTIONS_LAB_LIVE_VALIDATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _loop(config: LiveConfig) -> None:
    while not _stop.is_set():
        try:
            worker_tick(config, _state)
        except Exception as error:  # never let a bad tick kill the thread
            _state.failures += 1
            _state.last_event = {
                "at": datetime.now(timezone.utc).isoformat(),
                "kind": "tick_failed",
                "error": str(error)[:300],
            }
            log.warning("options_lab_tick_failed", extra={"error": str(error)[:300]})
        _stop.wait(POLL_SECONDS)


def start() -> None:
    """Start the collector thread. Safe to call once, from lifespan startup."""
    global _thread, _disabled_reason
    if not enabled():
        _disabled_reason = "OPTIONS_LAB_LIVE_VALIDATION is not set"
        log.info("options_lab_collector_disabled", extra={"reason": _disabled_reason})
        return
    if _thread is not None and _thread.is_alive():
        return
    try:
        config = LiveConfig.from_environment()
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
        config.report_directory.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        # A misconfigured lab must not stop the engine from booting.
        _disabled_reason = f"config failed: {str(error)[:200]}"
        log.warning(
            "options_lab_collector_config_failed", extra={"error": str(error)[:300]}
        )
        return
    _stop.clear()
    _state.started_at = datetime.now(timezone.utc).isoformat()
    _thread = threading.Thread(
        target=_loop, args=(config,), name="options-lab-collector", daemon=True
    )
    _thread.start()
    log.info(
        "options_lab_collector_started",
        extra={"database": str(config.database_path), "poll_seconds": POLL_SECONDS},
    )


def stop(timeout: float = 5.0) -> None:
    _stop.set()
    if _thread is not None and _thread.is_alive():
        _thread.join(timeout=timeout)


def status() -> dict[str, Any]:
    """What the collector has actually done, so its state is observable
    without shell access to the container."""
    return {
        "enabled": enabled(),
        "running": bool(_thread is not None and _thread.is_alive()),
        "disabled_reason": _disabled_reason,
        "started_at": _state.started_at or None,
        "poll_seconds": POLL_SECONDS,
        "ticks": _state.ticks,
        "collections": _state.collections,
        "failures": _state.failures,
        "last_bucket": _state.last_bucket,
        "last_event": _state.last_event,
        "reports_generated": sorted(_state.reported_dates),
    }
