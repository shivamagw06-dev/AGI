"""Institutional event calendar — drives event-boosted polling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Iterable

from app.ako.sessions import IST, now_ist


class EventKind(str, Enum):
    EARNINGS = "earnings"
    ANNUAL_RESULTS = "annual_results"
    DIVIDEND = "dividend"
    BUYBACK = "buyback"
    MERGER = "merger"
    CREDIT_RATING = "credit_rating"
    RBI_POLICY = "rbi_policy"
    UNION_BUDGET = "union_budget"
    REGULATORY = "regulatory"
    CUSTOM = "custom"


@dataclass(frozen=True)
class InstitutionalEvent:
    event_id: str
    kind: EventKind
    title: str
    event_date: date
    symbols: tuple[str, ...] = ()
    boost_multiplier: float = 2.0
    boost_hours_before: int = 6
    boost_hours_after: int = 12
    priority: int = 80  # 0–100


# Seed calendar for Sprint 6.5 demos / deterministic tests
SEED_EVENTS: tuple[InstitutionalEvent, ...] = (
    InstitutionalEvent(
        event_id="rbi_policy_seed",
        kind=EventKind.RBI_POLICY,
        title="RBI Monetary Policy",
        event_date=date(2026, 8, 6),
        symbols=(),
        boost_multiplier=3.0,
        boost_hours_before=24,
        boost_hours_after=24,
        priority=95,
    ),
    InstitutionalEvent(
        event_id="infy_earnings_seed",
        kind=EventKind.EARNINGS,
        title="Infosys Quarterly Results",
        event_date=date(2026, 7, 28),
        symbols=("INFY",),
        boost_multiplier=4.0,
        boost_hours_before=12,
        boost_hours_after=18,
        priority=90,
    ),
)


@dataclass
class EventCalendar:
    events: list[InstitutionalEvent] = field(default_factory=lambda: list(SEED_EVENTS))

    def add(self, event: InstitutionalEvent) -> None:
        self.events.append(event)

    def active_events(self, clock: datetime | None = None) -> list[InstitutionalEvent]:
        ist = now_ist(clock)
        active: list[InstitutionalEvent] = []
        for ev in self.events:
            start = datetime.combine(ev.event_date, datetime.min.time(), tzinfo=IST) - timedelta(
                hours=ev.boost_hours_before
            )
            end = datetime.combine(ev.event_date, datetime.max.time(), tzinfo=IST) + timedelta(
                hours=ev.boost_hours_after
            )
            # simpler end: event_date + after hours from midnight
            end = datetime.combine(ev.event_date, datetime.min.time(), tzinfo=IST) + timedelta(
                hours=24 + ev.boost_hours_after
            )
            if start <= ist <= end:
                active.append(ev)
        return sorted(active, key=lambda e: -e.priority)

    def boost_for_symbol(self, symbol: str | None, clock: datetime | None = None) -> float:
        """Return max boost multiplier applicable to a symbol (or global events)."""
        active = self.active_events(clock)
        if not active:
            return 1.0
        symbol = (symbol or "").upper() or None
        best = 1.0
        for ev in active:
            if not ev.symbols or (symbol and symbol in ev.symbols):
                best = max(best, ev.boost_multiplier)
            elif ev.kind in {EventKind.RBI_POLICY, EventKind.UNION_BUDGET}:
                best = max(best, min(ev.boost_multiplier, 2.0))
        return best

    def reasons(self, clock: datetime | None = None, symbol: str | None = None) -> list[str]:
        out = []
        symbol = (symbol or "").upper() or None
        for ev in self.active_events(clock):
            if not ev.symbols or (symbol and symbol in ev.symbols) or ev.kind in {
                EventKind.RBI_POLICY,
                EventKind.UNION_BUDGET,
            }:
                out.append(f"{ev.kind.value}:{ev.title}")
        return out
