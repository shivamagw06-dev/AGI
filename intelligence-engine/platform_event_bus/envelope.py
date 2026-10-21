"""EventEnvelope — immutable wire shape for bus events."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event(
    event_type: str,
    *,
    producer: str,
    payload: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    correlation_id: Optional[str] = None,
    event_id: Optional[str] = None,
    version: str = "peb.event.v1",
    timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Build a typed event envelope. Payload is deep-copied; bus never mutates caller data."""
    return {
        "schema": "peb01.event_envelope.v1",
        "event_id": event_id or f"evt:{uuid.uuid4().hex}",
        "event_type": str(event_type or "").strip(),
        "timestamp": timestamp or _now_iso(),
        "producer": str(producer or "unknown"),
        "correlation_id": correlation_id or f"corr:{uuid.uuid4().hex[:16]}",
        "payload": deepcopy(dict(payload or {})),
        "metadata": deepcopy(dict(metadata or {})),
        "version": version,
    }


def validate_envelope(event: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(event, Mapping):
        return ["event must be a mapping"]
    for field in ("event_id", "event_type", "timestamp", "producer", "correlation_id", "version"):
        if not event.get(field):
            errors.append(f"missing {field}")
    if "payload" not in event:
        errors.append("missing payload")
    return errors
