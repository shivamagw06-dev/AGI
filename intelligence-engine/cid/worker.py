"""Continuous four-worker company dossier population service."""

from __future__ import annotations

import json
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any

from cid.openai_dossier import status as openai_status
from cid.persistence import generated_age_seconds, latest_versions
from cid.production import generate_openai_dossier

STOP = Event()
DEFAULT_WORKERS = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_path() -> Path:
    root = Path(os.environ.get("KIP_DATA_DIR") or "/tmp")
    root.mkdir(parents=True, exist_ok=True)
    return root / "cid_dossier_worker_status.json"


def write_status(payload: dict[str, Any]) -> None:
    path = _status_path()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({**payload, "updated_at": _now()}, indent=2, default=str))
    temp.replace(path)


def read_status() -> dict[str, Any]:
    try:
        return json.loads(_status_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"status": "not_started", "workers": 0}


def warehouse_universe() -> list[str]:
    from institutional_warehouse import store

    symbols = store.entities("company_master")
    return sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})


def eligible_queue(*, refresh_days: float) -> tuple[list[str], int]:
    universe = warehouse_universe()
    versions = latest_versions()
    fresh_seconds = max(0.25, refresh_days) * 86400
    queue = []
    fresh = 0
    for ticker in universe:
        age = generated_age_seconds(versions.get(ticker) or {})
        if age is not None and age < fresh_seconds:
            fresh += 1
        else:
            queue.append(ticker)
    return queue, fresh


def _generate(ticker: str) -> dict[str, Any]:
    started = time.monotonic()
    result = generate_openai_dossier(ticker, refresh_evidence=True)
    persisted = (result.get("persistence") or {}).get("persisted")
    if result.get("ok") and not persisted:
        return {
            "ok": False,
            "ticker": ticker,
            "error": "dossier_not_persisted",
            "detail": result.get("persistence"),
            "runtime_seconds": round(time.monotonic() - started, 2),
        }
    return {
        "ok": bool(result.get("ok")),
        "ticker": ticker,
        "error": result.get("error"),
        "message": result.get("message"),
        "version": (result.get("persistence") or {}).get("version"),
        "runtime_seconds": round(time.monotonic() - started, 2),
    }


def run_forever() -> None:
    workers = max(1, min(4, int(os.environ.get("CID_DOSSIER_WORKERS", str(DEFAULT_WORKERS)))))
    refresh_days = float(os.environ.get("CID_DOSSIER_REFRESH_DAYS", "30"))
    idle_seconds = max(30, int(os.environ.get("CID_DOSSIER_IDLE_SECONDS", "300")))
    failures: dict[str, dict[str, Any]] = {}
    completed = 0

    write_status({"status": "starting", "workers": workers, "refresh_days": refresh_days})
    while not STOP.is_set():
        llm = openai_status()
        if not llm.get("enabled"):
            write_status({"status": "waiting_for_openai_key", "workers": workers, "openai": llm})
            STOP.wait(idle_seconds)
            continue
        try:
            queue, fresh = eligible_queue(refresh_days=refresh_days)
        except Exception as exc:
            write_status({"status": "degraded", "workers": workers, "error": str(exc)[:400]})
            STOP.wait(idle_seconds)
            continue

        now = time.time()
        queue = [
            ticker for ticker in queue
            if now >= float((failures.get(ticker) or {}).get("retry_at") or 0)
        ]
        if not queue:
            write_status(
                {
                    "status": "idle",
                    "workers": workers,
                    "universe": fresh,
                    "fresh": fresh,
                    "queued": 0,
                    "completed_this_process": completed,
                    "failures": len(failures),
                }
            )
            STOP.wait(idle_seconds)
            continue

        batch = queue[:workers]
        write_status(
            {
                "status": "running",
                "workers": workers,
                "universe": len(queue) + fresh,
                "fresh": fresh,
                "queued": len(queue),
                "active": batch,
                "completed_this_process": completed,
                "failures": len(failures),
            }
        )
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cid-dossier") as pool:
            futures = {pool.submit(_generate, ticker): ticker for ticker in batch}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {"ok": False, "ticker": ticker, "error": type(exc).__name__, "message": str(exc)[:300]}
                if result.get("ok"):
                    completed += 1
                    failures.pop(ticker, None)
                else:
                    attempts = int((failures.get(ticker) or {}).get("attempts") or 0) + 1
                    failures[ticker] = {
                        "attempts": attempts,
                        "error": result.get("error"),
                        "message": result.get("message"),
                        "retry_at": time.time() + min(21600, 60 * (2 ** min(attempts, 8))),
                    }


def stop(*_: Any) -> None:
    STOP.set()


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    run_forever()


if __name__ == "__main__":
    main()
