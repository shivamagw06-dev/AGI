"""Acquisition Scheduler — finance-agnostic job runner.

Collectors register themselves. The scheduler only executes jobs on interval.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from app.collectors.base import BaseCollector, CollectorJob

logger = logging.getLogger("kaip.scheduler")


@dataclass
class ScheduledJob:
    spec: CollectorJob
    runner: Callable[[], None]
    last_run_at: float | None = None
    run_count: int = 0
    last_error: str | None = None


class AcquisitionScheduler:
    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def register(self, collector: BaseCollector, runner: Callable[[], None]) -> CollectorJob:
        spec = collector.job_spec()
        with self._lock:
            self._jobs[spec.job_id] = ScheduledJob(spec=spec, runner=runner)
        logger.info(
            "registered job=%s interval_seconds=%s",
            spec.job_id,
            spec.interval_seconds,
        )
        return spec

    def list_jobs(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "job_id": j.spec.job_id,
                    "collector_id": j.spec.collector_id,
                    "interval_seconds": j.spec.interval_seconds,
                    "run_count": j.run_count,
                    "last_run_at": j.last_run_at,
                    "last_error": j.last_error,
                }
                for j in self._jobs.values()
            ]

    def run_once(self, job_id: str | None = None) -> None:
        with self._lock:
            jobs = list(self._jobs.values()) if job_id is None else [self._jobs[job_id]]
        for job in jobs:
            self._execute(job)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="kaip-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            now = time.time()
            with self._lock:
                jobs = list(self._jobs.values())
            for job in jobs:
                due = job.last_run_at is None or (now - job.last_run_at) >= job.spec.interval_seconds
                if due:
                    self._execute(job)
            self._stop.wait(1.0)

    def _execute(self, job: ScheduledJob) -> None:
        try:
            job.runner()
            job.last_error = None
        except Exception as exc:  # noqa: BLE001 — job boundary
            job.last_error = str(exc)
            logger.exception("job failed job_id=%s", job.spec.job_id)
        finally:
            job.last_run_at = time.time()
            job.run_count += 1
