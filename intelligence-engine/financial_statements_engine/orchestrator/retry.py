"""Exponential backoff retry policy for transient stage failures."""

from __future__ import annotations

from financial_statements_engine.orchestrator.schema import (
    BACKOFF_BASE_SECONDS,
    BACKOFF_MAX_SECONDS,
    MAX_RETRIES,
    TRANSIENT_ERROR_CODES,
)


def is_transient(error_code: str | None, detail: str | None = None) -> bool:
    code = (error_code or "").strip()
    if code in TRANSIENT_ERROR_CODES:
        return True
    text = f"{code} {detail or ''}".lower()
    return any(tok in text for tok in ("timeout", "rate", "temporar", "network", "unavailable", "503", "429"))


def should_retry(retries: int, *, error_code: str | None = None, detail: str | None = None) -> bool:
    if retries >= MAX_RETRIES:
        return False
    return is_transient(error_code, detail)


def backoff_seconds(retries: int) -> float:
    """retries is the attempt count about to be made (0-based after first failure)."""
    delay = BACKOFF_BASE_SECONDS * (2 ** max(0, retries))
    return float(min(delay, BACKOFF_MAX_SECONDS))
