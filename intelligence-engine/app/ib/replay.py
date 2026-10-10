"""Replay engine — by company, sector, time, type, producer, consumer, correlation."""

from __future__ import annotations

from typing import Any

from app.ib.delivery import DeliveryEngine
from app.ib.models import BusEvent
from app.ib.store import IbStore


def select_events_for_replay(
    store: IbStore,
    *,
    event_type: str | None = None,
    producer: str | None = None,
    aggregate_id: str | None = None,
    aggregate_type: str | None = None,
    correlation_id: str | None = None,
    company_symbol: str | None = None,
    sector: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
) -> list[BusEvent]:
    rows = [store.events[i] for i in store.event_order if i in store.events]
    if event_type:
        rows = [e for e in rows if e.event_type == event_type]
    if producer:
        rows = [e for e in rows if e.producer == producer]
    if aggregate_id:
        rows = [e for e in rows if e.aggregate_id == aggregate_id]
    if aggregate_type:
        rows = [e for e in rows if e.aggregate_type == aggregate_type]
    if correlation_id:
        rows = [e for e in rows if e.correlation_id == correlation_id]
    if company_symbol:
        sym = company_symbol.upper()
        rows = [
            e
            for e in rows
            if str((e.payload or {}).get("company_symbol") or "").upper() == sym
            or e.aggregate_id.upper() == sym
            or sym in [str(x).upper() for x in ((e.payload or {}).get("company_symbols") or [])]
        ]
    if sector:
        rows = [e for e in rows if str((e.payload or {}).get("sector") or "").lower() == sector.lower()]
    if since:
        rows = [e for e in rows if e.timestamp >= since]
    if until:
        rows = [e for e in rows if e.timestamp <= until]
    return rows[: max(1, min(limit, 500))]


def replay_events(
    store: IbStore,
    delivery: DeliveryEngine,
    *,
    consumer: str | None = None,
    **filters: Any,
) -> dict[str, Any]:
    selected = select_events_for_replay(store, **filters)
    deliveries = []
    for event in selected:
        # Temporarily narrow subscriptions if consumer filter set
        if consumer:
            original = dict(store.subscriptions)
            try:
                store.subscriptions = {
                    k: v for k, v in original.items() if v.subscriber == consumer
                }
                deliveries.extend(delivery.deliver(event, replay=True))
            finally:
                store.subscriptions = original
        else:
            deliveries.extend(delivery.deliver(event, replay=True))
        store.metrics.replayed += 1
    return {
        "replayed_events": len(selected),
        "deliveries": len(deliveries),
        "event_ids": [e.event_id for e in selected],
        "delivery_statuses": [d.status for d in deliveries],
    }
