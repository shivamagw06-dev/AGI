"""HTTP failure classification — permanent vs transient."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


PERMANENT_STATUS = frozenset({401, 402, 403, 404})
TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})


class RetryDecision(str, Enum):
    NEVER = "never"
    TRANSIENT = "transient"
    UNKNOWN = "unknown"


def classify_http_status(status: int | None) -> RetryDecision:
    if status is None:
        return RetryDecision.UNKNOWN
    code = int(status)
    if code in PERMANENT_STATUS:
        return RetryDecision.NEVER
    if code in TRANSIENT_STATUS:
        return RetryDecision.TRANSIENT
    # Other 4xx (e.g. 400, 409, 422) — do not retry.
    if 400 <= code < 500:
        return RetryDecision.NEVER
    if code >= 500:
        return RetryDecision.TRANSIENT
    return RetryDecision.UNKNOWN


def is_permanent_failure(status: int | None) -> bool:
    return classify_http_status(status) is RetryDecision.NEVER


def is_transient_failure(status: int | None) -> bool:
    return classify_http_status(status) is RetryDecision.TRANSIENT


@dataclass(frozen=True)
class ProviderPolicy:
    """Default Ask-path provider policy."""

    connect_timeout_sec: float = 2.0
    read_timeout_sec: float = 3.0
    overall_timeout_sec: float = 3.0
    max_attempts: int = 2
    backoff_base_sec: float = 0.25
    backoff_max_sec: float = 2.0
    circuit_fail_threshold: int = 3
    circuit_cooldown_sec: float = 900.0  # 15 minutes
