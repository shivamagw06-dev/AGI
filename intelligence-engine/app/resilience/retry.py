"""Exponential backoff retry — never retries permanent HTTP failures."""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from app.resilience.policy import RetryDecision, classify_http_status

T = TypeVar("T")


class PermanentProviderError(Exception):
    def __init__(self, provider_id: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.provider_id = provider_id
        self.status = status


class TransientProviderError(Exception):
    def __init__(self, provider_id: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.provider_id = provider_id
        self.status = status


def retry_sync(
    fn: Callable[[], T],
    *,
    max_attempts: int = 2,
    base_s: float = 0.25,
    max_s: float = 2.0,
    jitter: float = 0.2,
    retry_on: tuple[type[BaseException], ...] = (TransientProviderError, TimeoutError, OSError),
) -> T:
    """Retry ``fn`` with exponential backoff. PermanentProviderError is never retried."""
    attempts = max(1, int(max_attempts))
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except PermanentProviderError:
            raise
        except retry_on as exc:
            last = exc
            if attempt >= attempts:
                break
            delay = min(max_s, base_s * (2 ** (attempt - 1)))
            delay *= 1.0 + random.uniform(-jitter, jitter)
            time.sleep(max(0.0, delay))
        except Exception:
            raise
    assert last is not None
    raise last


def status_to_error(provider_id: str, status: int, body: str = "") -> Exception:
    decision = classify_http_status(status)
    msg = f"{provider_id} HTTP {status}: {body[:160]}"
    if decision is RetryDecision.NEVER:
        return PermanentProviderError(provider_id, msg, status=status)
    return TransientProviderError(provider_id, msg, status=status)
