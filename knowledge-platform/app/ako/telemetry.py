"""AKO execution telemetry — every scheduling/execution decision is observable."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ExecutionRecord:
    execution_id: str
    collector_id: str
    job_id: str
    session: str
    trigger_reason: str
    priority: int
    interval_seconds: int
    boost_multiplier: float
    started_at: str
    ended_at: str | None = None
    duration_ms: float | None = None
    success: bool | None = None
    error: str | None = None
    objects_collected: int = 0
    objects_published: int = 0
    learning_events: int = 0
    retry_count: int = 0
    queue_latency_ms: float = 0.0
    freshness_impact: str | None = None


@dataclass
class TelemetryHub:
    executions: list[ExecutionRecord] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    max_records: int = 500

    def begin(
        self,
        *,
        job_id: str,
        collector_id: str,
        session: str,
        trigger_reason: str,
        priority: int,
        interval_seconds: int,
        boost_multiplier: float,
        queue_latency_ms: float = 0.0,
    ) -> ExecutionRecord:
        rec = ExecutionRecord(
            execution_id=str(uuid4()),
            collector_id=collector_id,
            job_id=job_id,
            session=session,
            trigger_reason=trigger_reason,
            priority=priority,
            interval_seconds=interval_seconds,
            boost_multiplier=boost_multiplier,
            started_at=_iso(),
            queue_latency_ms=queue_latency_ms,
        )
        self.executions.append(rec)
        self._trim()
        return rec

    def complete(
        self,
        rec: ExecutionRecord,
        *,
        success: bool,
        error: str | None = None,
        objects_collected: int = 0,
        objects_published: int = 0,
        learning_events: int = 0,
        retry_count: int = 0,
        freshness_impact: str | None = None,
        started_mono: float | None = None,
    ) -> None:
        rec.ended_at = _iso()
        if started_mono is not None:
            rec.duration_ms = round((time.perf_counter() - started_mono) * 1000, 2)
        rec.success = success
        rec.error = error
        rec.objects_collected = objects_collected
        rec.objects_published = objects_published
        rec.learning_events = learning_events
        rec.retry_count = retry_count
        rec.freshness_impact = freshness_impact

    def log_decision(self, decision: dict[str, Any]) -> None:
        payload = {"ts": _iso(), **decision}
        self.decisions.append(payload)
        if len(self.decisions) > self.max_records:
            self.decisions = self.decisions[-self.max_records :]

    def snapshot(self) -> dict[str, Any]:
        recent = self.executions[-50:]
        successes = sum(1 for e in recent if e.success is True)
        failures = sum(1 for e in recent if e.success is False)
        return {
            "recent_executions": [asdict(e) for e in recent],
            "recent_decisions": self.decisions[-50:],
            "stats": {
                "executions_tracked": len(self.executions),
                "recent_successes": successes,
                "recent_failures": failures,
            },
        }

    def _trim(self) -> None:
        if len(self.executions) > self.max_records:
            self.executions = self.executions[-self.max_records :]
