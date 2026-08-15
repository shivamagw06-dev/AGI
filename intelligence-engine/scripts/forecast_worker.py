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
    os.environ.setdefault("FIE_BATCH", "2")
    os.environ.setdefault("FIE_INTERVAL_SECONDS", "120")
    os.environ.setdefault("STRATEGY_REGISTRY_REFRESH_SECONDS", "1800")
    os.environ.setdefault("ANSWER_PACK_MATERIALIZER_ENABLED", "true")
    os.environ.setdefault("ANSWER_PACK_MATERIALIZER_INTERVAL_SECONDS", "600")
    os.environ.setdefault("ANSWER_PACK_MATERIALIZER_BATCH", "10")

    from app.core.logging import configure_logging, get_logger
    from continuous_gather_learn.persist import write_gather_heartbeat
    from forecast_intelligence_engine.runtime import runtime_snapshot, start, stop
    from scripts.gather_worker import _publish_remote_heartbeat

    configure_logging()
    log = get_logger("agi.forecast_worker")
    boot = start()
    log.info("forecast_worker_started", extra=boot)
    try:
        registry_interval = max(300.0, float(os.environ["STRATEGY_REGISTRY_REFRESH_SECONDS"]))
    except (TypeError, ValueError):
        registry_interval = 1800.0
    try:
        answer_pack_interval = max(
            300.0,
            float(os.environ["ANSWER_PACK_MATERIALIZER_INTERVAL_SECONDS"]),
        )
    except (TypeError, ValueError):
        answer_pack_interval = 600.0
    stopping = {"value": False}

    def handle_stop(signum, _frame):  # noqa: ANN001
        stopping["value"] = True
        log.info("forecast_worker_signal", extra={"signum": int(signum)})

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    last_heartbeat = 0.0
    last_registry_refresh = 0.0
    last_answer_pack_refresh = 0.0
    answer_pack_status: dict = {"status": "pending"}
    while not stopping["value"]:
        if time.monotonic() - last_heartbeat >= 30.0:
            payload = {
                "phase": "forecast_runtime",
                "profile": "forecast_only",
                "FIE_RUNTIME": os.environ.get("FIE_RUNTIME"),
                "FIE_BATCH": os.environ.get("FIE_BATCH"),
                "forecast_runtime": runtime_snapshot(),
                "answer_pack_materializer": answer_pack_status,
            }
            try:
                write_gather_heartbeat(payload)
            except Exception as exc:  # noqa: BLE001
                log.warning("forecast_worker_local_heartbeat_failed", extra={"error": str(exc)[:200]})
            remote = _publish_remote_heartbeat(payload)
            if not remote.get("published"):
                log.warning("forecast_worker_heartbeat_failed", extra=remote)
            last_heartbeat = time.monotonic()
        if time.monotonic() - last_registry_refresh >= registry_interval:
            try:
                from strategy_lab.production import dashboard

                registry = dashboard(limit=20)
                from strategy_lab.paper import run as run_paper

                paper = run_paper(registry.get("strategies") or [])
                log.info(
                    "strategy_registry_refreshed",
                    extra={
                        "strategies": len(registry.get("strategies") or []),
                        "persistence": (registry.get("validation_registry") or {}).get("persistence"),
                        "paper": paper,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("strategy_registry_refresh_failed", extra={"error": str(exc)[:240]})
            last_registry_refresh = time.monotonic()
        if (
            os.environ.get("ANSWER_PACK_MATERIALIZER_ENABLED", "true").lower()
            in {"1", "true", "yes", "on"}
            and time.monotonic() - last_answer_pack_refresh >= answer_pack_interval
        ):
            try:
                from answer_packs.materializer import materialize_batch
                from continuous_gather_learn import persist as cgl_persist

                checkpoint = cgl_persist.get_checkpoint("answer_pack_materializer") or {}
                answer_pack_status = materialize_batch(
                    batch_size=max(
                        1,
                        int(os.environ.get("ANSWER_PACK_MATERIALIZER_BATCH") or 10),
                    ),
                    start_cursor=int(checkpoint.get("next_cursor") or 0),
                )
                cgl_persist.put_checkpoint("answer_pack_materializer", answer_pack_status)
                log.info(
                    "answer_pack_materializer_refreshed",
                    extra={
                        "attempted": answer_pack_status.get("attempted"),
                        "written": answer_pack_status.get("written"),
                        "unchanged": answer_pack_status.get("unchanged"),
                        "failures": len(answer_pack_status.get("failures") or []),
                        "next_cursor": answer_pack_status.get("next_cursor"),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                answer_pack_status = {"status": "failed", "error": str(exc)[:240]}
                log.warning("answer_pack_materializer_failed", extra=answer_pack_status)
            last_answer_pack_refresh = time.monotonic()
        time.sleep(5.0)
    stop()
    log.info("forecast_worker_stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
