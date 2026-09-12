"""PEB-01 — Platform Event Bus (in-process typed pub/sub)."""

from platform_event_bus.dispatcher import EventDispatcher, get_dispatcher
from platform_event_bus.publisher import EventPublisher, publish, soft_publish
from platform_event_bus.subscriber import EventSubscriber, subscribe
from platform_event_bus.schema import PEB01_VERSION, PEB01_WORKSTREAM_ID

__all__ = [
    "EventDispatcher",
    "EventPublisher",
    "EventSubscriber",
    "get_dispatcher",
    "publish",
    "soft_publish",
    "subscribe",
    "PEB01_VERSION",
    "PEB01_WORKSTREAM_ID",
]
