"""EventPublisher — offices publish only through this façade."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from platform_event_bus.dispatcher import get_dispatcher


class EventPublisher:
    """Thin façade so producers never depend on dispatcher internals."""

    def __init__(self, producer: str) -> None:
        self.producer = producer

    def publish(
        self,
        event_type: str,
        payload: Optional[Mapping[str, Any]] = None,
        *,
        metadata: Optional[Mapping[str, Any]] = None,
        correlation_id: Optional[str] = None,
        allow_unknown: bool = True,
    ) -> dict[str, Any]:
        return get_dispatcher().publish(
            event_type,
            producer=self.producer,
            payload=dict(payload or {}),
            metadata=dict(metadata or {}),
            correlation_id=correlation_id,
            allow_unknown=allow_unknown,
        )


def publish(
    event_type: str,
    *,
    producer: str,
    payload: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    correlation_id: Optional[str] = None,
    allow_unknown: bool = True,
) -> dict[str, Any]:
    return EventPublisher(producer).publish(
        event_type,
        payload,
        metadata=metadata,
        correlation_id=correlation_id,
        allow_unknown=allow_unknown,
    )


def soft_publish(
    event_type: str,
    *,
    producer: str,
    payload: Optional[Mapping[str, Any]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Never raise into office workflows — bus is optional soft infrastructure."""
    try:
        from platform_event_bus.flags import is_enabled

        if not is_enabled():
            return None
        return publish(
            event_type,
            producer=producer,
            payload=payload,
            metadata=metadata,
            correlation_id=correlation_id,
        )
    except Exception:  # noqa: BLE001
        return None
