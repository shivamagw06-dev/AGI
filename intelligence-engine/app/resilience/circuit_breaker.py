"""Process-wide provider circuit breakers (15-minute cool-down)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitSnapshot:
    provider_id: str
    state: str
    failures: int
    opened_until: float | None
    last_error: str | None
    last_status: int | None


@dataclass
class _Breaker:
    provider_id: str
    fail_threshold: int = 3
    cooldown_sec: float = 900.0
    failures: int = 0
    opened_until: float = 0.0
    last_error: str | None = None
    last_status: int | None = None
    successes: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self) -> bool:
        with self.lock:
            now = time.monotonic()
            if self.opened_until and now < self.opened_until:
                return False
            if self.opened_until and now >= self.opened_until:
                # Half-open: allow one probe.
                self.opened_until = 0.0
            return True

    def record_success(self) -> None:
        with self.lock:
            self.failures = 0
            self.opened_until = 0.0
            self.successes += 1
            self.last_error = None

    def record_failure(self, *, error: str | None = None, status: int | None = None) -> None:
        with self.lock:
            self.failures += 1
            self.last_error = (error or "")[:240] or None
            self.last_status = status
            if self.failures >= self.fail_threshold:
                self.opened_until = time.monotonic() + self.cooldown_sec

    def snapshot(self) -> CircuitSnapshot:
        with self.lock:
            now = time.monotonic()
            if self.opened_until and now < self.opened_until:
                state = CircuitState.OPEN.value
            elif self.failures > 0:
                state = CircuitState.HALF_OPEN.value
            else:
                state = CircuitState.CLOSED.value
            return CircuitSnapshot(
                provider_id=self.provider_id,
                state=state,
                failures=self.failures,
                opened_until=self.opened_until or None,
                last_error=self.last_error,
                last_status=self.last_status,
            )


class ProviderCircuitRegistry:
    def __init__(
        self,
        *,
        fail_threshold: int = 3,
        cooldown_sec: float = 900.0,
    ) -> None:
        self.fail_threshold = fail_threshold
        self.cooldown_sec = cooldown_sec
        self._breakers: dict[str, _Breaker] = {}
        self._lock = threading.Lock()

    def _get(self, provider_id: str) -> _Breaker:
        with self._lock:
            b = self._breakers.get(provider_id)
            if b is None:
                b = _Breaker(
                    provider_id=provider_id,
                    fail_threshold=self.fail_threshold,
                    cooldown_sec=self.cooldown_sec,
                )
                self._breakers[provider_id] = b
            return b

    def allow(self, provider_id: str) -> bool:
        return self._get(provider_id).allow()

    def success(self, provider_id: str) -> None:
        self._get(provider_id).record_success()

    def failure(
        self,
        provider_id: str,
        *,
        error: str | None = None,
        status: int | None = None,
    ) -> None:
        self._get(provider_id).record_failure(error=error, status=status)

    def status(self) -> dict[str, Any]:
        with self._lock:
            ids = list(self._breakers)
        return {pid: self._get(pid).snapshot().__dict__ for pid in ids}


_REGISTRY: ProviderCircuitRegistry | None = None
_REG_LOCK = threading.Lock()


def get_provider_circuits() -> ProviderCircuitRegistry:
    global _REGISTRY
    with _REG_LOCK:
        if _REGISTRY is None:
            _REGISTRY = ProviderCircuitRegistry()
        return _REGISTRY
