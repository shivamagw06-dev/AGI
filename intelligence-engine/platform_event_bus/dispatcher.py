"""EventDispatcher — synchronous in-process at-most-once delivery."""

from __future__ import annotations

import time
from copy import deepcopy
from threading import Lock
from typing import Any, Callable, Optional

from platform_event_bus.envelope import make_event, validate_envelope
from platform_event_bus.matching import matches
from platform_event_bus import registry as event_registry
from platform_event_bus import metrics as bus_metrics


EventHandler = Callable[[dict[str, Any]], Any]


class EventDispatcher:
    """
    In-process synchronous dispatcher.
    - Publisher never knows subscribers.
    - Handler failures are isolated (other handlers still run).
    - At-most-once within process; no persistence / retries.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._subs: list[dict[str, Any]] = []
        self._sub_seq = 0

    def subscribe(
        self,
        patterns: str | list[str],
        handler: EventHandler,
        *,
        subscriber_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> str:
        pats = [patterns] if isinstance(patterns, str) else list(patterns or [])
        if not pats:
            raise ValueError("at least one subscription pattern required")
        if not callable(handler):
            raise ValueError("handler must be callable")
        with self._lock:
            self._sub_seq += 1
            sid = subscriber_id or f"sub:{self._sub_seq}"
            # Replace existing subscriber_id if re-registering
            self._subs = [s for s in self._subs if s["subscriber_id"] != sid]
            self._subs.append(
                {
                    "subscriber_id": sid,
                    "name": name or sid,
                    "patterns": pats,
                    "handler": handler,
                }
            )
            bus_metrics.set_subscriber_count(len(self._subs))
        return sid

    def unsubscribe(self, subscriber_id: str) -> bool:
        with self._lock:
            before = len(self._subs)
            self._subs = [s for s in self._subs if s["subscriber_id"] != subscriber_id]
            bus_metrics.set_subscriber_count(len(self._subs))
            return len(self._subs) < before

    def list_subscribers(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "subscriber_id": s["subscriber_id"],
                    "name": s["name"],
                    "patterns": list(s["patterns"]),
                }
                for s in self._subs
            ]

    def publish(
        self,
        event_type: str,
        *,
        producer: str,
        payload: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        allow_unknown: bool = True,
    ) -> dict[str, Any]:
        event = make_event(
            event_type,
            producer=producer,
            payload=payload,
            metadata=metadata,
            correlation_id=correlation_id,
        )
        return self.dispatch(event, allow_unknown=allow_unknown)

    def dispatch(self, event: dict[str, Any], *, allow_unknown: bool = True) -> dict[str, Any]:
        errors = validate_envelope(event)
        if errors:
            raise ValueError("invalid event: " + "; ".join(errors))

        et = str(event["event_type"])
        known = event_registry.is_known(et)
        if not known and not allow_unknown:
            raise ValueError(f"unknown event type: {et}")

        # Deep-copy once for delivery isolation — handlers receive copies
        envelope = deepcopy(dict(event))
        bus_metrics.record_publish(et)

        with self._lock:
            subs = list(self._subs)

        # Stable ordering: subscription order
        matched = [s for s in subs if any(matches(p, et) for p in s["patterns"])]
        deliveries = []
        t0 = time.perf_counter()
        for sub in matched:
            ht0 = time.perf_counter()
            try:
                # Pass a fresh copy so handlers cannot mutate sibling deliveries
                sub["handler"](deepcopy(envelope))
                status = "ok"
                err = None
            except Exception as exc:  # noqa: BLE001 — isolate handler failures
                status = "error"
                err = f"{type(exc).__name__}: {exc}"
                bus_metrics.record_handler_failure(et, sub["subscriber_id"], err)
            elapsed_ms = (time.perf_counter() - ht0) * 1000.0
            deliveries.append(
                {
                    "subscriber_id": sub["subscriber_id"],
                    "name": sub["name"],
                    "status": status,
                    "error": err,
                    "latency_ms": round(elapsed_ms, 3),
                }
            )
            if status == "ok":
                bus_metrics.record_delivery(et, elapsed_ms)

        total_ms = (time.perf_counter() - t0) * 1000.0
        bus_metrics.record_dispatch(et, total_ms, len(matched))
        bus_metrics.remember_event(envelope, deliveries)

        return {
            "ok": True,
            "event": envelope,
            "known_type": known,
            "matched_subscribers": len(matched),
            "deliveries": deliveries,
            "dispatch_ms": round(total_ms, 3),
            "delivery_semantics": "at_most_once_in_process",
        }

    def reset_for_tests(self) -> None:
        with self._lock:
            self._subs.clear()
            self._sub_seq = 0
            bus_metrics.set_subscriber_count(0)


# Process-global dispatcher (replaceable later with broker-backed impl)
_DEFAULT = EventDispatcher()


def get_dispatcher() -> EventDispatcher:
    return _DEFAULT


def reset_bus_for_tests() -> None:
    _DEFAULT.reset_for_tests()
    bus_metrics.reset_for_tests()
    event_registry.reset_for_tests()
