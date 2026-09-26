"""IB store — event persistence, subscriptions, deliveries, DLQ, metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ib.config import DEFAULT_RETENTION_EVENTS
from app.ib.models import BusEvent, DeadLetter, DeliveryRecord, SchemaEntry, Subscription


@dataclass
class IbMetrics:
    published: int = 0
    delivered: int = 0
    failed: int = 0
    retries: int = 0
    dead_lettered: int = 0
    replayed: int = 0
    dropped: int = 0
    cache_invalidations: int = 0
    avg_publish_latency_ms: float = 0.0
    avg_delivery_latency_ms: float = 0.0
    last_publish_latency_ms: float = 0.0
    queue_depth: int = 0

    _pub_sum: float = field(default=0.0, repr=False)
    _del_sum: float = field(default=0.0, repr=False)

    def observe_publish(self, latency_ms: float) -> None:
        self.published += 1
        self.last_publish_latency_ms = latency_ms
        self._pub_sum += latency_ms
        self.avg_publish_latency_ms = round(self._pub_sum / max(1, self.published), 2)

    def observe_delivery(self, latency_ms: float, *, ok: bool, retry: bool = False) -> None:
        if ok:
            self.delivered += 1
        else:
            self.failed += 1
        if retry:
            self.retries += 1
        self._del_sum += latency_ms
        total = max(1, self.delivered + self.failed)
        self.avg_delivery_latency_ms = round(self._del_sum / total, 2)

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {
            "published": self.published,
            "delivered": self.delivered,
            "failed": self.failed,
            "retries": self.retries,
            "dead_lettered": self.dead_lettered,
            "replayed": self.replayed,
            "dropped": self.dropped,
            "cache_invalidations": self.cache_invalidations,
            "avg_publish_latency_ms": self.avg_publish_latency_ms,
            "avg_delivery_latency_ms": self.avg_delivery_latency_ms,
            "last_publish_latency_ms": self.last_publish_latency_ms,
            "queue_depth": self.queue_depth,
            "events_per_sec_estimate": 0.0,
        }


class IbStore:
    def __init__(self, *, retention: int = DEFAULT_RETENTION_EVENTS) -> None:
        self.retention = retention
        self.events: dict[str, BusEvent] = {}
        self.event_order: list[str] = []
        self.subscriptions: dict[str, Subscription] = {}
        self.deliveries: list[DeliveryRecord] = []
        self.dead_letters: dict[str, DeadLetter] = {}
        self.schemas: dict[str, SchemaEntry] = {}
        self.idempotency: set[str] = set()
        self.cache_invalidation_log: list[dict[str, Any]] = []
        self.metrics = IbMetrics()

    def put_event(self, event: BusEvent) -> BusEvent:
        self.events[event.event_id] = event
        self.event_order.append(event.event_id)
        self._trim()
        return event

    def _trim(self) -> None:
        while len(self.event_order) > self.retention:
            old = self.event_order.pop(0)
            self.events.pop(old, None)

    def put_subscription(self, sub: Subscription) -> Subscription:
        self.subscriptions[sub.subscription_id] = sub
        return sub

    def put_delivery(self, rec: DeliveryRecord) -> DeliveryRecord:
        self.deliveries.append(rec)
        self.deliveries = self.deliveries[-10000:]
        return rec

    def put_dlq(self, item: DeadLetter) -> DeadLetter:
        self.dead_letters[item.dlq_id] = item
        self.metrics.dead_lettered += 1
        return item

    def put_schema(self, entry: SchemaEntry) -> SchemaEntry:
        self.schemas[f"{entry.event_type}:{entry.schema_version}"] = entry
        return entry

    def has_idempotency(self, key: str) -> bool:
        return key in self.idempotency

    def mark_idempotency(self, key: str) -> None:
        self.idempotency.add(key)
        if len(self.idempotency) > 50000:
            self.idempotency = {d.idempotency_key for d in self.deliveries[-5000:] if d.idempotency_key}

    def snapshot(self) -> dict[str, Any]:
        return {
            "events": len(self.events),
            "subscriptions": len(self.subscriptions),
            "deliveries": len(self.deliveries),
            "dead_letters": len(self.dead_letters),
            "schemas": len(self.schemas),
            "cache_invalidations": len(self.cache_invalidation_log),
        }

    def list_events(
        self,
        *,
        event_type: str | None = None,
        producer: str | None = None,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
        limit: int = 50,
    ) -> list[BusEvent]:
        rows = [self.events[i] for i in reversed(self.event_order) if i in self.events]
        if event_type:
            rows = [e for e in rows if e.event_type == event_type]
        if producer:
            rows = [e for e in rows if e.producer == producer]
        if aggregate_id:
            rows = [e for e in rows if e.aggregate_id == aggregate_id]
        if correlation_id:
            rows = [e for e in rows if e.correlation_id == correlation_id]
        return rows[: max(1, min(limit, 500))]
