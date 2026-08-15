#!/usr/bin/env python3
"""Low-priority FIE sidecar sharing the intelligence engine's durable disk."""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    os.environ["AGI_ROLE"] = "gather_worker"
    os.environ.setdefault("FIE_RUNTIME", "true")
    os.environ.setdefault("FIE_BATCH", "1")
    os.environ.setdefault("FIE_INTERVAL_SECONDS", "180")

    from app.core.logging import configure_logging, get_logger
    from forecast_intelligence_engine.runtime import start, stop
    from scripts.gather_worker import _publish_remote_heartbeat

    configure_logging()
    log = get_logger("agi.forecast_worker")
    boot = start()
    log.info("forecast_worker_started", extra=boot)
    stopping = {"value": False}

    def handle_stop(signum, _frame):  # noqa: ANN001
        stopping["value"] = True
        log.info("forecast_worker_signal", extra={"signum": int(signum)})

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    last_heartbeat = 0.0
    while not stopping["value"]:
        if time.monotonic() - last_heartbeat >= 30.0:
            payload = {
                "phase": "forecast_runtime",
                "profile": "forecast_only",
                "FIE_RUNTIME": os.environ.get("FIE_RUNTIME"),
                "FIE_BATCH": os.environ.get("FIE_BATCH"),
            }
            remote = _publish_remote_heartbeat(payload)
            if not remote.get("published"):
                log.warning("forecast_worker_heartbeat_failed", extra=remote)
            last_heartbeat = time.monotonic()
        time.sleep(5.0)
    stop()
    log.info("forecast_worker_stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
