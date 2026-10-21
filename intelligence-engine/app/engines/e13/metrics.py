"""E13 metrics."""

from __future__ import annotations

import threading
import time
from typing import Any


class E13Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.runs = 0
        self.cache_hits = 0
        self.errors = 0
        self.latencies_ms: list[float] = []
        self.lookup_latencies_ms: list[float] = []

    def record_run(self, latency_ms: float, *, ok: bool) -> None:
        with self._lock:
            self.runs += 1
            if not ok:
                self.errors += 1
            self.latencies_ms.append(latency_ms)
            if len(self.latencies_ms) > 500:
                self.latencies_ms = self.latencies_ms[-500:]

    def record_lookup(self, latency_ms: float, *, cache_hit: bool) -> None:
        with self._lock:
            if cache_hit:
                self.cache_hits += 1
            self.lookup_latencies_ms.append(latency_ms)
            if len(self.lookup_latencies_ms) > 500:
                self.lookup_latencies_ms = self.lookup_latencies_ms[-500:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "runs": self.runs,
                "cache_hits": self.cache_hits,
                "errors": self.errors,
                "run_p95_ms": _p95(self.latencies_ms),
                "lookup_p95_ms": _p95(self.lookup_latencies_ms),
            }


class Timer:
    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0


def _p95(samples: list[float]) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    return ordered[int(0.95 * (len(ordered) - 1))]
