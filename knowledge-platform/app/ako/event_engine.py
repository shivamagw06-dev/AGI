"""Event Engine — register institutional events and surface active boosts."""

from __future__ import annotations

from datetime import date

from app.ako.calendar import EventCalendar, EventKind, InstitutionalEvent
from app.ako.sessions import now_ist


class EventEngine:
    def __init__(self, calendar: EventCalendar | None = None) -> None:
        self.calendar = calendar or EventCalendar()

    def register_event(
        self,
        *,
        kind: str,
        title: str,
        event_date: date,
        symbols: list[str] | None = None,
        boost_multiplier: float = 2.0,
        priority: int = 80,
        event_id: str | None = None,
    ) -> InstitutionalEvent:
        ev = InstitutionalEvent(
            event_id=event_id or f"{kind}:{event_date.isoformat()}:{','.join(symbols or [])}",
            kind=EventKind(kind),
            title=title,
            event_date=event_date,
            symbols=tuple(s.upper() for s in (symbols or [])),
            boost_multiplier=boost_multiplier,
            priority=priority,
        )
        self.calendar.add(ev)
        return ev

    def snapshot(self) -> dict:
        active = self.calendar.active_events()
        return {
            "as_of_ist": now_ist().isoformat(),
            "active_count": len(active),
            "active": [
                {
                    "event_id": e.event_id,
                    "kind": e.kind.value,
                    "title": e.title,
                    "event_date": e.event_date.isoformat(),
                    "symbols": list(e.symbols),
                    "boost_multiplier": e.boost_multiplier,
                    "priority": e.priority,
                }
                for e in active
            ],
            "total_registered": len(self.calendar.events),
        }
