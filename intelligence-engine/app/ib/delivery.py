"""Delivery engine — at-least-once, retries, DLQ, idempotent handlers."""

from __future__ import annotations

import time
from typing import Any, Callable

from app.ib.config import DEFAULT_BACKOFF_MS
from app.ib.models import BusEvent, DeadLetter, DeliveryRecord, Subscription, new_id
from app.ib.router import route_subscribers
from app.ib.store import IbStore

HandlerFn = Callable[[BusEvent, Subscription], Any]


class DeliveryEngine:
    def __init__(
        self,
        store: IbStore,
        *,
        retry_enabled: bool = True,
        dlq_enabled: bool = True,
        handlers: dict[str, HandlerFn] | None = None,
    ) -> None:
        self.store = store
        self.retry_enabled = retry_enabled
        self.dlq_enabled = dlq_enabled
        self.handlers: dict[str, HandlerFn] = handlers or {}

    def register_handler(self, subscriber: str, fn: HandlerFn) -> None:
        self.handlers[subscriber] = fn

    def deliver(self, event: BusEvent, *, replay: bool = False) -> list[DeliveryRecord]:
        subs = route_subscribers(event, self.store.subscriptions)
        records: list[DeliveryRecord] = []
        for sub in subs:
            records.append(self._deliver_one(event, sub, replay=replay))
        if not subs:
            event.status = "delivered"
        elif all(r.status == "delivered" for r in records):
            event.status = "replayed" if replay else "delivered"
        elif any(r.status == "dead_lettered" for r in records):
            event.status = "dead_lettered"
        else:
            event.status = "failed"
        return records

    def _deliver_one(self, event: BusEvent, sub: Subscription, *, replay: bool) -> DeliveryRecord:
        idem = f"{event.event_id}:{sub.subscriber}"
        if self.store.has_idempotency(idem) and not replay:
            rec = DeliveryRecord(
                delivery_id=new_id("dlv"),
                event_id=event.event_id,
                subscriber=sub.subscriber,
                subscription_id=sub.subscription_id,
                status="skipped",
                attempt=0,
                idempotency_key=idem,
                replay=replay,
                error="idempotent_skip",
            )
            self.store.put_delivery(rec)
            return rec

        handler = self.handlers.get(sub.subscriber)
        max_attempts = max(1, sub.retry_max if self.retry_enabled else 1)
        last_error = ""
        total_latency = 0.0

        for attempt in range(1, max_attempts + 1):
            t0 = time.perf_counter()
            try:
                if handler is None:
                    # No handler registered — acknowledge (subscription bookkeeping only)
                    pass
                else:
                    handler(event, sub)
                latency = (time.perf_counter() - t0) * 1000
                total_latency += latency
                self.store.mark_idempotency(idem)
                rec = DeliveryRecord(
                    delivery_id=new_id("dlv"),
                    event_id=event.event_id,
                    subscriber=sub.subscriber,
                    subscription_id=sub.subscription_id,
                    status="delivered",
                    attempt=attempt,
                    latency_ms=round(total_latency, 2),
                    idempotency_key=idem,
                    replay=replay,
                )
                self.store.put_delivery(rec)
                self.store.metrics.observe_delivery(total_latency, ok=True, retry=attempt > 1)
                return rec
            except Exception as exc:  # soft isolation per subscriber
                latency = (time.perf_counter() - t0) * 1000
                total_latency += latency
                last_error = str(exc) or exc.__class__.__name__
                event.retry_count = attempt
                if attempt < max_attempts and self.retry_enabled:
                    backoff = DEFAULT_BACKOFF_MS[min(attempt - 1, len(DEFAULT_BACKOFF_MS) - 1)]
                    time.sleep(backoff / 1000.0)
                    self.store.metrics.retries += 1
                    continue

        # Exhausted retries
        status = "dead_lettered" if (self.dlq_enabled and sub.failure_strategy == "dlq") else "failed"
        if status == "dead_lettered":
            self.store.put_dlq(
                DeadLetter(
                    dlq_id=new_id("dlq"),
                    event_id=event.event_id,
                    subscriber=sub.subscriber,
                    subscription_id=sub.subscription_id,
                    error=last_error,
                    attempts=max_attempts,
                    payload_snapshot=dict(event.payload or {}),
                )
            )
        elif sub.failure_strategy == "drop":
            self.store.metrics.dropped += 1
            status = "skipped"

        rec = DeliveryRecord(
            delivery_id=new_id("dlv"),
            event_id=event.event_id,
            subscriber=sub.subscriber,
            subscription_id=sub.subscription_id,
            status=status,
            attempt=max_attempts,
            latency_ms=round(total_latency, 2),
            error=last_error,
            idempotency_key=idem,
            replay=replay,
        )
        self.store.put_delivery(rec)
        self.store.metrics.observe_delivery(total_latency, ok=False, retry=max_attempts > 1)
        return rec
