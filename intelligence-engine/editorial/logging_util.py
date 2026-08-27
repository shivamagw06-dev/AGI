"""Safe editorial logging — never log API keys."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("agib.editorial")

_KEY_PATTERNS = re.compile(
    r"(api[_-]?key|authorization|bearer\s+[a-z0-9\-_.]+|AIza[0-9A-Za-z\-_]{10,})",
    re.I,
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if re.search(r"(api)?_?key|token|secret|authorization", str(k), re.I):
                out[k] = "[REDACTED]"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str):
        return _KEY_PATTERNS.sub("[REDACTED]", value)
    return value


def log_editorial_event(
    *,
    event: str,
    question: str | None = None,
    structured: dict[str, Any] | None = None,
    prompt: str | None = None,
    response: str | None = None,
    latency_ms: float | None = None,
    token_usage: dict[str, Any] | None = None,
    error: str | None = None,
    provider: str | None = None,
    mode: str | None = None,
    cache_hit: bool | None = None,
) -> None:
    payload = {
        "event": event,
        "provider": provider,
        "mode": mode,
        "question": (question or "")[:500],
        "structured_intelligence": _redact(structured or {}),
        "prompt": _redact((prompt or "")[:4000]),
        "gemini_response": _redact((response or "")[:4000]),
        "latency_ms": latency_ms,
        "token_usage": _redact(token_usage or {}),
        "cache_hit": cache_hit,
        "error": _redact(error) if error else None,
    }
    if error:
        logger.warning("editorial_event %s", payload)
    else:
        logger.info("editorial_event %s", payload)
