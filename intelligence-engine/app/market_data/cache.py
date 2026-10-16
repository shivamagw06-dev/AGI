"""TTL response cache with duplicate in-flight coalescing (WBS DATA-003)."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float
    created_at: float


class MarketDataCache:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry[Any]] = {}
        self._inflight: dict[str, asyncio.Future[Any]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.coalesced = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            if time.monotonic() >= entry.expires_at:
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_s: float) -> None:
        now = time.monotonic()
        with self._lock:
            self._store[key] = CacheEntry(value=value, expires_at=now + ttl_s, created_at=now)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._inflight.clear()

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total else 0.0

    def stats(self) -> dict[str, float | int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "coalesced": self.coalesced,
            "size": len(self._store),
            "hit_ratio": self.hit_ratio,
        }

    async def get_or_set(
        self,
        key: str,
        ttl_s: float,
        factory: Callable[[], Awaitable[T]],
    ) -> tuple[T, bool]:
        """Return (value, cache_hit). Coalesces duplicate concurrent misses."""
        cached = self.get(key)
        if cached is not None:
            return cached, True

        loop = asyncio.get_running_loop()
        with self._lock:
            existing = self._inflight.get(key)
            if existing is not None:
                self.coalesced += 1
                future: asyncio.Future[Any] = existing
                owner = False
            else:
                future = loop.create_future()
                self._inflight[key] = future
                owner = True

        if not owner:
            value = await asyncio.shield(future)
            return value, False

        try:
            value = await factory()
            self.set(key, value, ttl_s)
            if not future.done():
                future.set_result(value)
            return value, False
        except Exception as exc:
            if not future.done():
                future.set_exception(exc)
                # The owner raises the original exception directly. If no
                # coalesced waiter exists, asyncio would otherwise report
                # "Future exception was never retrieved" even though the
                # provider failure was handled by the caller.
                future.exception()
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)
