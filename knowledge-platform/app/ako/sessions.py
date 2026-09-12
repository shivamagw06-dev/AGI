"""Market Clock + Session State — IST institutional sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class MarketSession(str, Enum):
    PRE_MARKET = "PRE_MARKET"
    MARKET_OPEN = "MARKET_OPEN"
    LIVE_MARKET = "LIVE_MARKET"
    POST_MARKET = "POST_MARKET"
    AFTER_CLOSE = "AFTER_CLOSE"
    OVERNIGHT = "OVERNIGHT"
    WEEKEND = "WEEKEND"
    HOLIDAY = "HOLIDAY"


# NSE holidays seed for Sprint 6.5 (extend via config later)
NSE_HOLIDAYS_2026: set[date] = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),   # Holi (approx seed)
    date(2026, 3, 31),  # Ram Navami (approx seed)
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 10, 20), # Diwali (approx seed)
    date(2026, 11, 8),  # Guru Nanak (approx seed)
    date(2026, 12, 25), # Christmas
}


@dataclass(frozen=True)
class SessionState:
    session: MarketSession
    as_of_ist: datetime
    is_trading_day: bool
    allow_live_polling: bool
    allow_heavy_rebuild: bool
    label: str


def now_ist(clock: datetime | None = None) -> datetime:
    if clock is None:
        return datetime.now(IST)
    if clock.tzinfo is None:
        return clock.replace(tzinfo=IST)
    return clock.astimezone(IST)


def is_nse_holiday(d: date) -> bool:
    return d in NSE_HOLIDAYS_2026


def resolve_session(clock: datetime | None = None) -> SessionState:
    ist = now_ist(clock)
    d = ist.date()
    t = ist.timetz().replace(tzinfo=None) if False else ist.time()

    if ist.weekday() >= 5:
        return SessionState(
            session=MarketSession.WEEKEND,
            as_of_ist=ist,
            is_trading_day=False,
            allow_live_polling=False,
            allow_heavy_rebuild=True,
            label="Weekend — minimal polling",
        )
    if is_nse_holiday(d):
        return SessionState(
            session=MarketSession.HOLIDAY,
            as_of_ist=ist,
            is_trading_day=False,
            allow_live_polling=False,
            allow_heavy_rebuild=True,
            label="Exchange holiday — minimal polling",
        )

    # Trading day windows (IST)
    if time(8, 30) <= t < time(9, 15):
        session = MarketSession.PRE_MARKET
        label = "Pre-market warm-up"
        live, heavy = True, False
    elif time(9, 15) <= t < time(9, 30):
        session = MarketSession.MARKET_OPEN
        label = "Market open — aggressive cadence"
        live, heavy = True, False
    elif time(9, 30) <= t < time(15, 30):
        session = MarketSession.LIVE_MARKET
        label = "Live market"
        live, heavy = True, False
    elif time(15, 30) <= t < time(16, 0):
        session = MarketSession.POST_MARKET
        label = "Post-market close processing"
        live, heavy = True, False
    elif time(16, 0) <= t < time(19, 0):
        session = MarketSession.AFTER_CLOSE
        label = "After close — bhavcopy & actions"
        live, heavy = False, False
    elif t >= time(23, 0) or t < time(6, 0):
        session = MarketSession.OVERNIGHT
        label = "Overnight rebuild window"
        live, heavy = False, True
    else:
        # 19:00–23:00 quiet evening
        session = MarketSession.AFTER_CLOSE
        label = "Evening quiet — reduced polling"
        live, heavy = False, False

    return SessionState(
        session=session,
        as_of_ist=ist,
        is_trading_day=True,
        allow_live_polling=live,
        allow_heavy_rebuild=heavy,
        label=label,
    )


def next_session_boundary(clock: datetime | None = None) -> datetime:
    """Next IST boundary useful for Mission Control 'next transition'."""
    ist = now_ist(clock)
    boundaries = [
        time(6, 0),
        time(8, 30),
        time(9, 15),
        time(9, 30),
        time(15, 30),
        time(16, 0),
        time(19, 0),
        time(23, 0),
    ]
    for b in boundaries:
        candidate = datetime.combine(ist.date(), b, tzinfo=IST)
        if candidate > ist:
            return candidate
    return datetime.combine(ist.date() + timedelta(days=1), time(6, 0), tzinfo=IST)
