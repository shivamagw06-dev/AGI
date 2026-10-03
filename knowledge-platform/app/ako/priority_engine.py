"""Priority Engine — order due jobs so institutional-critical work runs first."""

from __future__ import annotations

from app.ako.schedule_engine import ScheduleDecision


class PriorityEngine:
    def order(self, decisions: list[ScheduleDecision]) -> list[ScheduleDecision]:
        due = [d for d in decisions if d.should_run]
        return sorted(
            due,
            key=lambda d: (-d.priority, d.interval_seconds, d.job_id),
        )
