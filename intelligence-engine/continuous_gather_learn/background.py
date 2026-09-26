"""Background thread for Continuous Gather → Learn — never on the Ask path."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from continuous_gather_learn.flags import interval_sec, is_enabled

log = logging.getLogger("agi.continuous_gather_learn")

_STOP = threading.Event()
_THREAD: threading.Thread | None = None
_LAST: dict[str, Any] = {}


def last_status() -> dict[str, Any]:
    return dict(_LAST)


def _loop() -> None:
    # Stagger first run so /v1/health stays responsive after boot.
    time.sleep(min(90.0, interval_sec() / 3))
    while not _STOP.is_set():
        if not is_enabled():
            _STOP.wait(60.0)
            continue
        try:
            from continuous_gather_learn.orchestrator import run_cycle

            result = run_cycle()
            _LAST.clear()
            _LAST.update(
                {
                    "at": result.get("generated_at"),
                    "ok": result.get("ok"),
                    "run_id": result.get("run_id"),
                    "slot": result.get("slot"),
                    "latency_ms": result.get("latency_ms"),
                    "volumes": result.get("volumes"),
                }
            )
            log.info(
                "cgl_cycle",
                extra={
                    "ok": result.get("ok"),
                    "slot": result.get("slot"),
                    "run_id": result.get("run_id"),
                    "latency_ms": result.get("latency_ms"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("cgl_cycle_failed", extra={"error": str(exc)[:200]})
            _LAST.clear()
            _LAST.update({"at": time.time(), "ok": False, "error": str(exc)[:200]})
        _STOP.wait(interval_sec())


def start_background_loop() -> dict[str, Any]:
    global _THREAD
    if not is_enabled():
        return {"ok": False, "started": False, "reason": "CONTINUOUS_GATHER_LEARN=false"}
    if _THREAD and _THREAD.is_alive():
        return {"ok": True, "started": False, "already_running": True, "interval_sec": interval_sec()}
    _STOP.clear()
    _THREAD = threading.Thread(target=_loop, name="cgl-background", daemon=True)
    _THREAD.start()
    return {"ok": True, "started": True, "interval_sec": interval_sec(), "ask_isolated": True}


def stop_background_loop() -> dict[str, Any]:
    global _THREAD
    _STOP.set()
    t = _THREAD
    if t and t.is_alive():
        t.join(timeout=5.0)
    _THREAD = None
    return {"ok": True, "stopped": True}
