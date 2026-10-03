"""Retry with exponential backoff + jitter (WBS DATA-004)."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class RetryError(Exception):
    def __init__(self, message: str, errors: list[BaseException]) -> None:
        self.errors = errors
        super().__init__(message)


def compute_backoff_s(
    attempt: int,
    *,
    base_s: float = 0.05,
    factor: float = 2.0,
    max_s: float = 2.0,
    jitter: float = 0.2,
) -> float:
    """attempt is 0-indexed failure count before next try."""
    delay = min(max_s, base_s * (factor**attempt))
    if jitter <= 0:
        return delay
    return max(0.0, delay * (1.0 + random.uniform(-jitter, jitter)))


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 5,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    base_s: float = 0.05,
    factor: float = 2.0,
    max_s: float = 2.0,
    jitter: float = 0.2,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    sleeper = sleep or asyncio.sleep
    errors: list[BaseException] = []
    for attempt in range(max_attempts):
        try:
            return await fn()
        except retry_on as exc:
            errors.append(exc)
            if attempt + 1 >= max_attempts:
                break
            await sleeper(
                compute_backoff_s(
                    attempt,
                    base_s=base_s,
                    factor=factor,
                    max_s=max_s,
                    jitter=jitter,
                )
            )
    raise RetryError(f"exhausted {max_attempts} attempts", errors)
