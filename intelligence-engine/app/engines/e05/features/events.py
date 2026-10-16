"""PIT corporate event object parsing + deterministic calendar synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.engines.e05.mapping import IMPORTANCE, P0_EVENT_TYPES


@dataclass
class PitEvent:
    event_id: str
    event_type: str
    symbol: str
    event_time: str  # ISO date or datetime; PIT announcement/effective
    actual: float | None = None
    consensus: float | None = None
    guidance_delta: float | None = None
    importance_override: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def event_date(self) -> date:
        raw = self.event_time[:10]
        return date.fromisoformat(raw)


def parse_event_objects(
    symbol: str,
    raw_events: list[dict[str, Any]] | None,
    *,
    as_of: str,
) -> list[PitEvent]:
    """Parse point-in-time event objects. Drop events with event_time > as_of for past-only
    fields is NOT done here — calendar may include upcoming. Look-ahead for surprise actuals
    is enforced in the state builder (actuals only when event_time <= as_of).
    """
    out: list[PitEvent] = []
    as_of_d = date.fromisoformat(as_of[:10])
    for i, raw in enumerate(raw_events or []):
        if not isinstance(raw, dict):
            continue
        et = str(raw.get("event_type") or "").strip().lower()
        if et not in P0_EVENT_TYPES:
            continue
        etime = str(raw.get("event_time") or raw.get("as_of") or "")
        if not etime:
            continue
        # Reject events whose event_time date is wildly in the future beyond upcoming window
        try:
            ed = date.fromisoformat(etime[:10])
        except ValueError:
            continue
        eid = str(raw.get("event_id") or f"{symbol}_{et}_{etime[:10]}_{i}")
        out.append(
            PitEvent(
                event_id=eid,
                event_type=et,
                symbol=symbol.upper(),
                event_time=etime,
                actual=_f(raw.get("actual") if ed <= as_of_d else None),
                consensus=_f(raw.get("consensus")),
                guidance_delta=_f(raw.get("guidance_delta")),
                importance_override=_f(raw.get("importance")),
                meta={k: v for k, v in raw.items() if k not in {
                    "event_id", "event_type", "event_time", "as_of",
                    "actual", "consensus", "guidance_delta", "importance",
                }},
            )
        )
    out.sort(key=lambda e: (e.event_time, e.event_id))
    return out


def synthesize_calendar(symbol: str, as_of: str, panel: dict[str, Any]) -> list[PitEvent]:
    """Deterministic PIT calendar stub when panels lack explicit events.

    Never uses MarketDataClient / raw calendars — only symbol seed + panel scalars.
    """
    as_of_d = date.fromisoformat(as_of[:10])
    h = _seed(symbol)
    # Recent earnings ~ 12 + (h%10) days ago
    earn_ago = 8 + (h % 12)
    earn_d = as_of_d - timedelta(days=earn_ago)
    # Upcoming earnings ~ 20–40 days ahead
    earn_next = as_of_d + timedelta(days=20 + (h % 15))
    # Dividend ex-date recent or upcoming
    div_offset = (h // 3) % 25 - 10
    div_d = as_of_d + timedelta(days=div_offset)
    # Guidance change alongside recent earnings
    guide_d = earn_d

    eps_cons = float(panel.get("ep_ttm") or 0.10)
    # Small deterministic surprise from seed
    surp_ratio = ((h % 17) - 8) / 100.0  # -0.08 .. +0.08
    eps_act = eps_cons * (1.0 + surp_ratio)
    guide_delta = ((h % 11) - 5) / 100.0

    events = [
        PitEvent(
            event_id=f"{symbol}_earn_q_{earn_d.isoformat()}",
            event_type="earn_q",
            symbol=symbol.upper(),
            event_time=earn_d.isoformat(),
            actual=round(eps_act, 6),
            consensus=round(eps_cons, 6),
        ),
        PitEvent(
            event_id=f"{symbol}_eps_surprise_{earn_d.isoformat()}",
            event_type="eps_surprise",
            symbol=symbol.upper(),
            event_time=earn_d.isoformat(),
            actual=round(eps_act, 6),
            consensus=round(eps_cons, 6),
        ),
        PitEvent(
            event_id=f"{symbol}_guidance_{guide_d.isoformat()}",
            event_type="guidance",
            symbol=symbol.upper(),
            event_time=guide_d.isoformat(),
            guidance_delta=round(guide_delta, 6),
        ),
        PitEvent(
            event_id=f"{symbol}_dividend_{div_d.isoformat()}",
            event_type="dividend",
            symbol=symbol.upper(),
            event_time=div_d.isoformat(),
        ),
        PitEvent(
            event_id=f"{symbol}_earn_q_{earn_next.isoformat()}",
            event_type="earn_q",
            symbol=symbol.upper(),
            event_time=earn_next.isoformat(),
            consensus=round(eps_cons, 6),
        ),
    ]
    # Occasional CA from seed
    if h % 5 == 0:
        ca_d = as_of_d - timedelta(days=3 + (h % 7))
        events.append(
            PitEvent(
                event_id=f"{symbol}_split_{ca_d.isoformat()}",
                event_type="split",
                symbol=symbol.upper(),
                event_time=ca_d.isoformat(),
            )
        )
    elif h % 5 == 1:
        ca_d = as_of_d - timedelta(days=2 + (h % 5))
        events.append(
            PitEvent(
                event_id=f"{symbol}_bonus_{ca_d.isoformat()}",
                event_type="bonus",
                symbol=symbol.upper(),
                event_time=ca_d.isoformat(),
            )
        )
    elif h % 5 == 2:
        ca_d = as_of_d + timedelta(days=5 + (h % 9))
        events.append(
            PitEvent(
                event_id=f"{symbol}_rights_{ca_d.isoformat()}",
                event_type="rights",
                symbol=symbol.upper(),
                event_time=ca_d.isoformat(),
            )
        )
    return events


def event_importance(event: PitEvent) -> float:
    if event.importance_override is not None:
        return max(0.0, min(1.0, float(event.importance_override)))
    return float(IMPORTANCE.get(event.event_type, 0.40))


def days_delta(as_of: str, event_time: str) -> int:
    """Positive = days since event; negative = days until event."""
    a = date.fromisoformat(as_of[:10])
    e = date.fromisoformat(event_time[:10])
    return (a - e).days


def _seed(symbol: str) -> int:
    h = 2166136261
    for ch in symbol.upper():
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return int(h)


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
