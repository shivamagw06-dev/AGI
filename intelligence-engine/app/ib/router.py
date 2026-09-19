"""Event routing — broadcast, targeted, topic, filtered, version-aware."""

from __future__ import annotations

from typing import Any

from app.ib.models import BusEvent, Subscription


def matches_subscription(event: BusEvent, sub: Subscription) -> bool:
    if not sub.enabled:
        return False
    if sub.version_compat and event.schema_version and sub.version_compat != event.schema_version:
        # Version-aware: allow same major family prefix
        if not (
            event.schema_version.startswith("ib-event-v")
            and sub.version_compat.startswith("ib-event-v")
        ):
            return False
    if sub.event_types and event.event_type not in sub.event_types:
        return False
    if sub.categories and event.category and event.category not in sub.categories:
        return False
    if event.routing == "targeted" and event.targets:
        if sub.subscriber not in event.targets:
            return False
    if event.routing == "topic" and event.topics:
        # Subscription filter may declare topics of interest
        wanted = list((sub.filter or {}).get("topics") or [])
        if wanted and not set(wanted).intersection(event.topics):
            return False
    # Filtered routing / subscription filters
    filt = sub.filter or {}
    if filt.get("aggregate_type") and filt["aggregate_type"] != event.aggregate_type:
        return False
    if filt.get("aggregate_id") and filt["aggregate_id"] != event.aggregate_id:
        return False
    if filt.get("producer") and filt["producer"] != event.producer:
        return False
    payload_eq = filt.get("payload_equals") or {}
    if isinstance(payload_eq, dict):
        for k, v in payload_eq.items():
            if (event.payload or {}).get(k) != v:
                return False
    return True


def route_subscribers(event: BusEvent, subscriptions: dict[str, Subscription]) -> list[Subscription]:
    """Return matching subscriptions ordered by priority."""
    priority_rank = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    matched = [s for s in subscriptions.values() if matches_subscription(event, s)]
    matched.sort(key=lambda s: (priority_rank.get(s.priority, 9), s.subscriber))
    return matched


def explain_routing(event: BusEvent, subscriptions: dict[str, Subscription]) -> dict[str, Any]:
    matched = route_subscribers(event, subscriptions)
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "routing": event.routing,
        "targets": list(event.targets),
        "topics": list(event.topics),
        "matched_subscribers": [s.subscriber for s in matched],
        "matched_subscription_ids": [s.subscription_id for s in matched],
        "skipped": [
            s.subscriber
            for s in subscriptions.values()
            if s.subscriber not in {m.subscriber for m in matched}
        ],
    }
