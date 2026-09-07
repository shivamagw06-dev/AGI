"""Institutional provider resilience — circuit breakers, smart retries, hard timeouts.

Rules:
- Never retry permanent failures: 401, 402, 403, 404
- Retry only transient: 429, 500, 502, 503, 504, timeouts
- Exponential backoff with jitter
- Circuit breaker skips unhealthy providers for a cool-down window
- No network call may wait indefinitely
"""

from app.resilience.circuit_breaker import ProviderCircuitRegistry, get_provider_circuits
from app.resilience.policy import (
    PERMANENT_STATUS,
    TRANSIENT_STATUS,
    RetryDecision,
    classify_http_status,
    is_permanent_failure,
    is_transient_failure,
)
from app.resilience.retry import retry_sync

__all__ = [
    "PERMANENT_STATUS",
    "TRANSIENT_STATUS",
    "ProviderCircuitRegistry",
    "RetryDecision",
    "classify_http_status",
    "get_provider_circuits",
    "is_permanent_failure",
    "is_transient_failure",
    "retry_sync",
]
