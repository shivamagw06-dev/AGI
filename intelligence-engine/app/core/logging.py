from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone


_QUERY_SECRET = re.compile(
    r"(?i)([?&](?:token|api[_-]?key|apikey|access_token)=)[^&\s\"']+"
)
_BEARER_SECRET = re.compile(r"(?i)(bearer\s+)[a-z0-9._~+\-/=]{12,}")
_OPENAI_SECRET = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")
_SECRET_FIELD = re.compile(
    r"^(?:authorization|token|api[_-]?key|apikey|access[_-]?token|secret)$", re.I
)


def redact_secrets(value):
    """Remove common credentials from log messages and structured extras."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SECRET_FIELD.match(str(key)) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_secrets(item) for item in value]
    if not isinstance(value, str):
        return value
    text = _QUERY_SECRET.sub(r"\1[REDACTED]", value)
    text = _BEARER_SECRET.sub(r"\1[REDACTED]", text)
    return _OPENAI_SECRET.sub("sk-[REDACTED]", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_secrets(record.getMessage()),
        }
        for key in ("run_id", "agent_id", "desk", "extra"):
            if hasattr(record, key):
                payload[key] = redact_secrets(getattr(record, key))
        if record.exc_info:
            payload["exc_info"] = redact_secrets(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
