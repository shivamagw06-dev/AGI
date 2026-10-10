"""ORCH L2 metrics."""

from __future__ import annotations

import threading
from typing import Any


class L2Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.batches = 0
        self.features_built = 0
        self.features_failed = 0
        self.features_skipped = 0
        self.retries = 0
        self.timeouts = 0
        self.ready_events = 0
        self.durations_ms: list[float] = []

    def record_batch(
        self,
        *,
        built: int,
        failed: int,
        skipped: int,
        duration_ms: float,
    ) -> None:
        with self._lock:
            self.batches += 1
            self.features_built += built
            self.features_failed += failed
            self.features_skipped += skipped
            self.durations_ms.append(duration_ms)
            if len(self.durations_ms) > 500:
                self.durations_ms = self.durations_ms[-500:]

    def record_retry(self) -> None:
        with self._lock:
            self.retries += 1

    def record_timeout(self) -> None:
        with self._lock:
            self.timeouts += 1

    def record_ready(self) -> None:
        with self._lock:
            self.ready_events += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            p95 = None
            if self.durations_ms:
                ordered = sorted(self.durations_ms)
                p95 = ordered[int(0.95 * (len(ordered) - 1))]
            return {
                "batches": self.batches,
                "features_built": self.features_built,
                "features_failed": self.features_failed,
                "features_skipped": self.features_skipped,
                "retries": self.retries,
                "timeouts": self.timeouts,
                "ready_events": self.ready_events,
                "batch_duration_p95_ms": p95,
            }
