"""Feature Registry metrics."""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class FeatureMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.lookups = 0
        self.compute_count = 0
        self.errors = 0
        self.latency_lookup_ms: list[float] = []
        self.latency_compute_ms: list[float] = []
        self.by_feature_compute: dict[str, int] = defaultdict(int)

    def record_lookup(self, latency_ms: float) -> None:
        with self._lock:
            self.lookups += 1
            self.latency_lookup_ms.append(latency_ms)
            if len(self.latency_lookup_ms) > 512:
                self.latency_lookup_ms = self.latency_lookup_ms[-512:]

    def record_compute(self, feature_id: str, latency_ms: float, *, ok: bool) -> None:
        with self._lock:
            self.compute_count += 1
            self.by_feature_compute[feature_id] += 1
            self.latency_compute_ms.append(latency_ms)
            if not ok:
                self.errors += 1
            if len(self.latency_compute_ms) > 512:
                self.latency_compute_ms = self.latency_compute_ms[-512:]

    @staticmethod
    def _p95(samples: list[float]) -> float | None:
        if not samples:
            return None
        ordered = sorted(samples)
        idx = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        return ordered[idx]

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "lookups": self.lookups,
                "compute_count": self.compute_count,
                "errors": self.errors,
                "lookup_p95_ms": self._p95(self.latency_lookup_ms),
                "compute_p95_ms": self._p95(self.latency_compute_ms),
                "by_feature_compute": dict(self.by_feature_compute),
            }


class Timer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0
