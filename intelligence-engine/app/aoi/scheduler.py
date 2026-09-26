"""Intelligent scheduler — cron labels, queues, retries, prioritisation."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from app.aoi.models import ScheduleJob
from app.aoi.sources_config import DEFAULT_SCHEDULE
from app.aoi.store import AoiStore


class Scheduler:
    def __init__(self, store: AoiStore, *, jobs: list[dict[str, Any]] | None = None) -> None:
        self.store = store
        self.jobs: dict[str, ScheduleJob] = {}
        for row in jobs or DEFAULT_SCHEDULE:
            job = ScheduleJob.model_validate(row)
            self.jobs[job.job_id] = job

    def list_jobs(self) -> list[ScheduleJob]:
        return sorted(self.jobs.values(), key=lambda j: (j.priority, j.job_id))

    def enqueue_due(self, *, cadence_filter: str | None = None) -> list[ScheduleJob]:
        """Select due jobs by priority into the process queue."""
        due = []
        for job in self.list_jobs():
            if not job.enabled:
                continue
            if cadence_filter and job.cadence != cadence_filter and cadence_filter != "all":
                continue
            due.append(job)
        due.sort(key=lambda j: j.priority)
        self.store.queue = [j.job_id for j in due]
        self.store.metrics.queue_length = len(self.store.queue)
        self.store.metrics.scheduler_health = "ok" if due else "idle"
        return due

    def mark_run(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if not job:
            return
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        self.jobs[job_id] = job.model_copy(update={"last_run_at": now, "next_run_hint": _next_hint(job.cadence)})

    def status(self) -> dict[str, Any]:
        return {
            "scheduler_health": self.store.metrics.scheduler_health,
            "queue_length": len(self.store.queue),
            "queue": list(self.store.queue),
            "jobs": [j.model_dump(mode="json") for j in self.list_jobs()],
        }


def _next_hint(cadence: str) -> str:
    return {
        "hourly": "within_1h",
        "earnings_hourly": "within_1h_earnings_season",
        "daily": "within_24h",
        "event": "on_release",
        "cron": "cron_expression",
    }.get(cadence, "unspecified")
