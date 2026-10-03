"""Retry policy — transient vs permanent failures (FSE-02 §10)."""

from __future__ import annotations

import random
from typing import Any

from financial_statements_engine.collection.schema import (
    BACKOFF_CAP_S,
    MAX_ATTEMPTS,
    NON_RETRYABLE_HTTP,
    RETRYABLE_HTTP,
)


def is_retryable_http(status_code: int | None) -> bool:
    if status_code is None:
        return True
    code = int(status_code)
    if code in NON_RETRYABLE_HTTP:
        return False
    if code in RETRYABLE_HTTP:
        return True
    # 2xx/3xx not failures; other 4xx permanent; other 5xx transient
    if 200 <= code < 400:
        return False
    if 400 <= code < 500:
        return False
    return code >= 500


def classify_error(exc: BaseException | None = None, *, http_status: int | None = None) -> str:
    """Return ``transient`` or ``permanent``."""
    if http_status is not None:
        return "transient" if is_retryable_http(http_status) else "permanent"
    if exc is None:
        return "transient"
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    permanent_markers = ("not found", "404", "forbidden", "401", "403", "unsupported")
    if any(m in msg for m in permanent_markers):
        return "permanent"
    if "timeout" in name or "timeout" in msg or "connection" in name or "connection" in msg:
        return "transient"
    return "transient"


def backoff_seconds(attempt: int, *, cap: float = BACKOFF_CAP_S, jitter_ms: int = 250) -> float:
    """Exponential backoff: min(2^attempt, cap) + jitter."""
    a = max(0, int(attempt))
    base = min(float(2**a), float(cap))
    jitter = random.uniform(0, max(0, jitter_ms) / 1000.0)
    return base + jitter


def should_retry(attempt: int, classification: str, *, max_attempts: int = MAX_ATTEMPTS) -> bool:
    if classification != "transient":
        return False
    return int(attempt) < int(max_attempts)


def retry_plan(attempt: int, *, http_status: int | None = None, exc: BaseException | None = None) -> dict[str, Any]:
    classification = classify_error(exc, http_status=http_status)
    retry = should_retry(attempt, classification)
    return {
        "classification": classification,
        "retry": retry,
        "attempt": int(attempt),
        "max_attempts": MAX_ATTEMPTS,
        "backoff_s": backoff_seconds(attempt) if retry else 0.0,
        "http_status": http_status,
    }
