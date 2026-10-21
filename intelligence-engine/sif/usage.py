"""SIF production usage / reasoning traces."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class SifUsageStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self.sector_counts: Counter[str] = Counter()
        self.traces: list[dict[str, Any]] = []
        self.queries = 0
        self.blocked_recommendations = 0

    def record(self, trace: dict[str, Any]) -> None:
        with self._lock:
            self.queries += 1
            sid = trace.get("sector_id")
            if sid:
                self.sector_counts[sid] += 1
            if trace.get("recommendation_blocked"):
                self.blocked_recommendations += 1
            row = {"ts": datetime.now(timezone.utc).isoformat(), **trace}
            self.traces.append(row)
            self.traces = self.traces[-200:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "queries": self.queries,
                "blocked_recommendations": self.blocked_recommendations,
                "sector_counts": dict(self.sector_counts),
                "recent_traces": list(reversed(self.traces[-20:])),
            }

    def reset(self) -> None:
        with self._lock:
            self.sector_counts = Counter()
            self.traces = []
            self.queries = 0
            self.blocked_recommendations = 0


_STORE = SifUsageStore()


def get_sif_store() -> SifUsageStore:
    return _STORE


def reset_sif_store() -> None:
    get_sif_store().reset()
