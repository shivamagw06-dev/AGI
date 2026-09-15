"""Lightweight in-process metrics for KAIP ops."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Metrics:
    collector_runs: dict[str, int] = field(default_factory=dict)
    accepted_events: int = 0
    rejected_events: int = 0
    duplicate_events: int = 0
    published_objects: int = 0
    learning_events: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_run(self, collector_id: str, *, accepted: int, rejected: int, duplicates: int, published: int, learning: int) -> None:
        with self._lock:
            self.collector_runs[collector_id] = self.collector_runs.get(collector_id, 0) + 1
            self.accepted_events += accepted
            self.rejected_events += rejected
            self.duplicate_events += duplicates
            self.published_objects += published
            self.learning_events += learning

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "collector_runs": dict(self.collector_runs),
                "accepted_events": self.accepted_events,
                "rejected_events": self.rejected_events,
                "duplicate_events": self.duplicate_events,
                "published_objects": self.published_objects,
                "learning_events": self.learning_events,
            }


METRICS = Metrics()
