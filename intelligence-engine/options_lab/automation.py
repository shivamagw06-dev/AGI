"""Market-hours automation for Upstox collection and daily V1 reports."""

from __future__ import annotations

import argparse
import json
import signal
import time
from datetime import datetime, time as clock_time, timezone
from typing import Any

from .store import OptionEvidenceStore
from .upstox_live import IST, LiveConfig, UpstoxLiveError, collect_once
from .validation import generate_daily_report


MARKET_OPEN = clock_time(9, 15)
MARKET_CLOSE = clock_time(15, 30)
REPORT_TIME = clock_time(15, 45)


def _is_market_session(now: datetime) -> bool:
    local = now.astimezone(IST)
    return (
        local.weekday() < 5
        and MARKET_OPEN <= local.time().replace(tzinfo=None) <= MARKET_CLOSE
    )


def _collection_bucket(now: datetime) -> str:
    local = now.astimezone(IST)
    minutes = local.hour * 60 + local.minute
    return f"{local.date().isoformat()}:{minutes // 15}"


def _emit(event: str, payload: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "event": event,
                "at": datetime.now(timezone.utc).isoformat(),
                **payload,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def collect_command(config: LiveConfig, *, force: bool) -> int:
    now = datetime.now(timezone.utc)
    if not force and not _is_market_session(now):
        _emit("collection_skipped", {"reason": "outside_nse_market_session"})
        return 0
    try:
        result = collect_once(config, captured_at=now)
    except UpstoxLiveError as error:
        _emit("collection_failed", {"error": str(error)})
        return 2
    _emit("collection_completed", result)
    return 0


def report_command(config: LiveConfig, report_date: str | None) -> int:
    local_date = report_date or datetime.now(IST).date().isoformat()
    store = OptionEvidenceStore(config.database_path)
    result = generate_daily_report(
        store,
        local_date,
        config.report_directory,
    )
    _emit("daily_report_completed", result)
    return 0


def run_worker(config: LiveConfig, *, poll_seconds: int = 10) -> int:
    stopping = False

    def stop(_signal, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    last_bucket: str | None = None
    reported_dates: set[str] = set()
    _emit(
        "worker_started",
        {
            "database": str(config.database_path),
            "reports": str(config.report_directory),
            "underlying": config.underlying_key,
        },
    )
    while not stopping:
        now = datetime.now(timezone.utc)
        local = now.astimezone(IST)
        if _is_market_session(now):
            bucket = _collection_bucket(now)
            if bucket != last_bucket:
                exit_code = collect_command(config, force=True)
                last_bucket = bucket
                if exit_code:
                    _emit(
                        "worker_warning",
                        {"reason": "collection_failed", "exit_code": exit_code},
                    )
        elif (
            local.weekday() < 5
            and local.time().replace(tzinfo=None) >= REPORT_TIME
            and local.date().isoformat() not in reported_dates
        ):
            try:
                report_command(config, local.date().isoformat())
                reported_dates.add(local.date().isoformat())
            except Exception as error:
                _emit("daily_report_failed", {"error": str(error)[:1000]})
        time.sleep(max(2, poll_seconds))
    _emit("worker_stopped", {})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pricing Engine V1 live validation automation"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument(
        "--force",
        action="store_true",
        help="collect outside market hours for an explicit diagnostic",
    )
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--date", help="YYYY-MM-DD; defaults to today in IST")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--poll-seconds", type=int, default=10)
    subparsers.add_parser("status")
    subparsers.add_parser("init")
    arguments = parser.parse_args()
    config = LiveConfig.from_environment()

    if arguments.command == "collect":
        return collect_command(config, force=arguments.force)
    if arguments.command == "report":
        return report_command(config, arguments.date)
    if arguments.command == "run":
        return run_worker(config, poll_seconds=arguments.poll_seconds)
    store = OptionEvidenceStore(config.database_path)
    if arguments.command == "status":
        _emit("status", store.status())
    else:
        _emit("initialized", {"database": str(config.database_path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
