"""Token-bucket rate limiter per provider (WBS DATA-002)."""

from __future__ import annotations

import threading
import time


class RateLimitExceeded(Exception):
    def __init__(self, provider_id: str, retry_after_s: float) -> None:
        self.provider_id = provider_id
        self.retry_after_s = retry_after_s
        super().__init__(f"rate limited: {provider_id}; retry_after_s={retry_after_s:.3f}")


class TokenBucketRateLimiter:
    def __init__(self, rate_per_second: float, burst: int) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be > 0")
        if burst < 1:
            raise ValueError("burst must be >= 1")
        self.rate_per_second = rate_per_second
        self.burst = float(burst)
        self._tokens = float(burst)
        self._updated_at = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated_at
        self._updated_at = now
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate_per_second)

    def try_acquire(self, tokens: float = 1.0) -> float | None:
        """Acquire tokens. Returns None on success, else retry_after seconds."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return None
            deficit = tokens - self._tokens
            return deficit / self.rate_per_second

    def acquire(self, tokens: float = 1.0, *, block: bool = False, timeout_s: float = 0.0) -> None:
        deadline = time.monotonic() + timeout_s if block else None
        while True:
            retry_after = self.try_acquire(tokens)
            if retry_after is None:
                return
            if not block:
                raise RateLimitExceeded("bucket", retry_after)
            if deadline is not None and time.monotonic() + retry_after > deadline:
                raise RateLimitExceeded("bucket", retry_after)
            time.sleep(min(retry_after, 0.05))


class ProviderRateLimitRegistry:
    def __init__(self) -> None:
        self._limiters: dict[str, TokenBucketRateLimiter] = {}
        self._lock = threading.Lock()

    def configure(self, provider_id: str, rate_per_second: float, burst: int) -> None:
        with self._lock:
            self._limiters[provider_id] = TokenBucketRateLimiter(rate_per_second, burst)

    def acquire(self, provider_id: str) -> None:
        with self._lock:
            limiter = self._limiters.get(provider_id)
        if limiter is None:
            return
        retry_after = limiter.try_acquire()
        if retry_after is not None:
            raise RateLimitExceeded(provider_id, retry_after)
