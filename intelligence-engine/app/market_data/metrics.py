"""In-process market-data metrics (cache hits, latency, provider health)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class LatencyStat:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    samples: list[float] = field(default_factory=list)

    def observe(self, latency_ms: float) -> None:
        self.count += 1
        self.total_ms += latency_ms
        self.max_ms = max(self.max_ms, latency_ms)
        self.samples.append(latency_ms)
        if len(self.samples) > 512:
            self.samples = self.samples[-512:]

    def p95_ms(self) -> float | None:
        if not self.samples:
            return None
        ordered = sorted(self.samples)
        idx = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        return ordered[idx]


class MarketDataMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.cache_hits = 0
        self.cache_misses = 0
        self.cold_fetches = 0
        self.provider_success: dict[str, int] = defaultdict(int)
        self.provider_failure: dict[str, int] = defaultdict(int)
        self.failover_count = 0
        self.latency_cache = LatencyStat()
        self.latency_cold = LatencyStat()

    def record_cache_hit(self, latency_ms: float) -> None:
        with self._lock:
            self.cache_hits += 1
            self.latency_cache.observe(latency_ms)

    def record_cold_fetch(self, provider_id: str, latency_ms: float, *, ok: bool) -> None:
        with self._lock:
            self.cold_fetches += 1
            self.cache_misses += 1
            self.latency_cold.observe(latency_ms)
            if ok:
                self.provider_success[provider_id] += 1
            else:
                self.provider_failure[provider_id] += 1

    def record_failover(self) -> None:
        with self._lock:
            self.failover_count += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            total = self.cache_hits + self.cache_misses
            return {
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_ratio": (self.cache_hits / total) if total else 0.0,
                "cold_fetches": self.cold_fetches,
                "failover_count": self.failover_count,
                "provider_success": dict(self.provider_success),
                "provider_failure": dict(self.provider_failure),
                "latency_cache_p95_ms": self.latency_cache.p95_ms(),
                "latency_cold_p95_ms": self.latency_cold.p95_ms(),
            }


class Timer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0
