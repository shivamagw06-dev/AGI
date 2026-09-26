"""Collector Dispatcher — execute due jobs with retry / backoff / DLQ. Never collects itself."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.ako.schedule_engine import ScheduleDecision
from app.ako.telemetry import ExecutionRecord, TelemetryHub

logger = logging.getLogger("kaip.ako.dispatcher")


@dataclass
class DeadLetter:
    job_id: str
    collector_id: str
    error: str
    attempts: int
    last_trigger_reason: str
    created_at: float = field(default_factory=time.time)


@dataclass
class RegisteredJob:
    job_id: str
    collector_id: str
    runner: Callable[[], Any]
    last_run_at: float | None = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error: str | None = None
    last_interval_seconds: int | None = None
    last_trigger_reason: str | None = None
    session_runs: dict[str, str] = field(default_factory=dict)  # session_date -> session name
    consecutive_failures: int = 0
    source_available: bool = True


class CollectorDispatcher:
    def __init__(
        self,
        telemetry: TelemetryHub,
        *,
        max_retries: int = 2,
        backoff_seconds: tuple[float, ...] = (1.0, 3.0, 8.0),
    ) -> None:
        self.telemetry = telemetry
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.jobs: dict[str, RegisteredJob] = {}
        self.dead_letters: list[DeadLetter] = []
        self.queue_depth = 0

    def register(self, job_id: str, collector_id: str, runner: Callable[[], Any]) -> None:
        self.jobs[job_id] = RegisteredJob(job_id=job_id, collector_id=collector_id, runner=runner)
        logger.info("ako registered job=%s collector=%s", job_id, collector_id)

    def dispatch(self, decision: ScheduleDecision, *, session_key: str) -> ExecutionRecord | None:
        job = self.jobs.get(decision.job_id)
        if not job or not decision.should_run:
            return None

        self.queue_depth = max(0, self.queue_depth)
        t0 = time.perf_counter()
        rec = self.telemetry.begin(
            job_id=decision.job_id,
            collector_id=job.collector_id,
            session=decision.session.value,
            trigger_reason=decision.trigger_reason,
            priority=decision.priority,
            interval_seconds=decision.interval_seconds,
            boost_multiplier=decision.boost_multiplier,
            queue_latency_ms=0.0,
        )

        attempts = 0
        last_error: str | None = None
        result_payload: Any = None
        while attempts <= self.max_retries:
            try:
                result_payload = job.runner()
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001 — job boundary
                last_error = str(exc)
                attempts += 1
                if attempts <= self.max_retries:
                    delay = self.backoff_seconds[min(attempts - 1, len(self.backoff_seconds) - 1)]
                    time.sleep(delay)
                logger.exception("ako job failed job=%s attempt=%s", decision.job_id, attempts)

        success = last_error is None
        collected = published = learning = 0
        if success and result_payload is not None:
            collected, published, learning = _extract_counts(result_payload)

        self.telemetry.complete(
            rec,
            success=success,
            error=last_error,
            objects_collected=collected,
            objects_published=published,
            learning_events=learning,
            retry_count=attempts if not success else max(0, attempts),
            freshness_impact="updated" if published else "unchanged",
            started_mono=t0,
        )

        job.last_run_at = time.time()
        job.run_count += 1
        job.last_interval_seconds = decision.interval_seconds
        job.last_trigger_reason = decision.trigger_reason
        job.session_runs[session_key] = decision.session.value
        if success:
            job.success_count += 1
            job.consecutive_failures = 0
            job.last_error = None
            job.source_available = True
        else:
            job.failure_count += 1
            job.consecutive_failures += 1
            job.last_error = last_error
            if job.consecutive_failures >= 5:
                job.source_available = False
                self.dead_letters.append(
                    DeadLetter(
                        job_id=job.job_id,
                        collector_id=job.collector_id,
                        error=last_error or "unknown",
                        attempts=attempts,
                        last_trigger_reason=decision.trigger_reason,
                    )
                )
                if len(self.dead_letters) > 200:
                    self.dead_letters = self.dead_letters[-200:]
        return rec


def _extract_counts(result: Any) -> tuple[int, int, int]:
    """Best-effort extract from PipelineResult-like objects."""
    try:
        collected = len(getattr(result, "accepted", []) or []) + len(getattr(result, "raw_events", []) or [])
        published = len(getattr(result, "knowledge_objects", []) or [])
        learning = len(getattr(result, "learning_events", []) or [])
        if collected == 0 and hasattr(result, "accepted"):
            collected = len(result.accepted)
        return collected, published, learning
    except Exception:
        return 0, 0, 0
