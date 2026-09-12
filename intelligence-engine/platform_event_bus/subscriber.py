"""EventSubscriber helpers — register handlers against patterns."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence, Union

from platform_event_bus.dispatcher import EventHandler, get_dispatcher


class EventSubscriber:
    def __init__(self, subscriber_id: str, *, name: Optional[str] = None) -> None:
        self.subscriber_id = subscriber_id
        self.name = name or subscriber_id

    def on(
        self,
        patterns: Union[str, Sequence[str]],
        handler: EventHandler,
    ) -> str:
        return get_dispatcher().subscribe(
            list(patterns) if not isinstance(patterns, str) else patterns,
            handler,
            subscriber_id=self.subscriber_id,
            name=self.name,
        )

    def off(self) -> bool:
        return get_dispatcher().unsubscribe(self.subscriber_id)


def subscribe(
    patterns: Union[str, Sequence[str]],
    handler: Callable[[dict[str, Any]], Any],
    *,
    subscriber_id: Optional[str] = None,
    name: Optional[str] = None,
) -> str:
    return get_dispatcher().subscribe(patterns, handler, subscriber_id=subscriber_id, name=name)
