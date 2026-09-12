"""Scheduled FAA collector, isolated from the Ask request path.

Default policy (Asia/Kolkata):
  * 01:00 — full bounded daily acquisition, starts only inside a one-hour window.
  * 18:00 — small filings/regulatory sweep after the market close.
"""

from __future__ import annotations

from datetime import datetime
import logging
import os
import threading
import time
from typing import Any, Callable
from zoneinfo import ZoneInfo

log = logging.getLogger("agi.faa.background")
IST = ZoneInfo("Asia/Kolkata")

_STOP = threading.Event()
_THREAD: threading.Thread | None = None
_LAST_RUN_DATE: dict[str, str] = {}


def _env_truthy(name: str, default: str = "1") -> bool:
    return str(os.environ.get(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(os.environ.get(name) or default)))
    except ValueError:
        return default


def _limit(mode: str) -> int:
    default = 3 if mode == "nightly" else 2
    key = "FAA_NIGHTLY_LIMIT" if mode == "nightly" else "FAA_EVENING_LIMIT"
    return _env_int(key, default, 1, 8)


def _max_runtime_sec(mode: str) -> int:
    default = 3_600 if mode == "nightly" else 900
    key = "FAA_NIGHTLY_MAX_RUNTIME_SEC" if mode == "nightly" else "FAA_EVENING_MAX_RUNTIME_SEC"
    return _env_int(key, default, 60, 3_600)


def collector_enabled() -> bool:
    return _env_truthy("FAA_BACKGROUND_COLLECTOR", "1")


def due_mode(now: datetime | None = None) -> str | None:
    current = (now or datetime.now(IST)).astimezone(IST)
    date_key = current.date().isoformat()
    nightly_hour = _env_int("FAA_NIGHTLY_HOUR_IST", 1, 0, 23)
    evening_hour = _env_int("FAA_EVENING_HOUR_IST", 18, 0, 23)
    if current.hour == nightly_hour and _LAST_RUN_DATE.get("nightly") != date_key:
        return "nightly"
    if (
        _env_truthy("FAA_EVENING_FILINGS_SWEEP", "1")
        and current.hour == evening_hour
        and _LAST_RUN_DATE.get("evening_filings") != date_key
    ):
        return "evening_filings"
    return None


def run_collector_once(faa: Any, *, mode: str = "nightly") -> dict[str, Any]:
    """Run one bounded scheduled collection cycle."""
    if faa is None:
        return {"ok": False, "error": "faa_unbound", "mode": mode}
    if hasattr(faa, "refresh_snapshots"):
        return faa.refresh_snapshots(
            limit_per_query=_limit(mode),
            mode=mode,
            max_runtime_sec=_max_runtime_sec(mode),
        )
    return {"ok": False, "error": "no_refresh_method", "mode": mode}


def _loop(faa_factory: Callable[[], Any]) -> None:
    # No collection on boot. Poll cheaply until a configured IST window opens.
    while not _STOP.wait(30.0):
        if not collector_enabled():
            continue
        mode = due_mode()
        if not mode:
            continue
        date_key = datetime.now(IST).date().isoformat()
        # Reserve the slot before work begins, preventing duplicate starts.
        _LAST_RUN_DATE[mode] = date_key
        try:
            result = run_collector_once(faa_factory(), mode=mode)
            log.info(
                "faa_scheduled_cycle",
                extra={
                    "mode": mode,
                    "ok": bool(result.get("ok", True)),
                    "queries": result.get("queries") or len(result.get("runs") or []),
                    "errors": len(result.get("errors") or []),
                    "deferred": result.get("deferred") or 0,
                },
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("faa_scheduled_cycle_failed", extra={"mode": mode, "error": str(exc)[:200]})


def schedule_status() -> dict[str, Any]:
    return {
        "timezone": "Asia/Kolkata",
        "nightly": {
            "hour": _env_int("FAA_NIGHTLY_HOUR_IST", 1, 0, 23),
            "window_minutes": 60,
            "max_runtime_seconds": _max_runtime_sec("nightly"),
            "limit_per_query": _limit("nightly"),
            "last_run_date": _LAST_RUN_DATE.get("nightly"),
        },
        "evening_filings": {
            "enabled": _env_truthy("FAA_EVENING_FILINGS_SWEEP", "1"),
            "hour": _env_int("FAA_EVENING_HOUR_IST", 18, 0, 23),
            "max_runtime_seconds": _max_runtime_sec("evening_filings"),
            "limit_per_query": _limit("evening_filings"),
            "last_run_date": _LAST_RUN_DATE.get("evening_filings"),
        },
    }


def start_background_collector(faa_factory: Callable[[], Any]) -> dict[str, Any]:
    global _THREAD
    if not collector_enabled():
        return {"started": False, "reason": "disabled", "schedule": schedule_status()}
    if _THREAD is not None and _THREAD.is_alive():
        return {"started": False, "reason": "already_running", "schedule": schedule_status()}
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, args=(faa_factory,), name="faa-scheduled-collector", daemon=True)
    _THREAD.start()
    return {"started": True, "schedule": schedule_status()}


def stop_background_collector() -> None:
    _STOP.set()
