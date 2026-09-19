"""E05-002 Event State Builder — importance, surprise, decay, composite."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.e05.features.builder import EventPanel
from app.engines.e05.features.events import PitEvent, days_delta, event_importance
from app.engines.e05.mapping import RECENT_WINDOW_DAYS, UPCOMING_WINDOW_DAYS
from app.engines.e05.models.decay import decay_weight, half_life_for
from app.engines.e05.models.surprise import (
    eps_surprise,
    guidance_delta_score,
    signed_impact,
    surprise_score_0_100,
)


@dataclass
class EventSummary:
    event_id: str
    event_type: str
    event_time: str
    status: str  # upcoming | recent | active
    days_since: int | None
    days_until: int | None
    importance: float
    surprise: float | None
    surprise_score: float
    decay_halflife_days: float
    decay_weight: float
    event_score: float
    expected_impact: float


@dataclass
class EventStateRow:
    symbol: str
    as_of: str
    sector_id: str | None
    upcoming_events: list[EventSummary]
    recent_events: list[EventSummary]
    days_since_event: float | None
    days_until_event: float | None
    event_importance: float
    surprise_score: float
    decay_factor: float
    composite_score: float
    expected_event_impact: float
    primary_event_type: str | None
    label: str
    side: str
    confidence: float
    stale_inputs: list[str] = field(default_factory=list)
    discovery: str = "pit_objects"
    event_meta: dict[str, float] = field(default_factory=dict)


def compute_universe_states(panels: dict[str, EventPanel]) -> dict[str, EventStateRow]:
    out: dict[str, EventStateRow] = {}
    for sym in sorted(panels.keys()):
        out[sym] = _compute_one(panels[sym])
    return out


def _compute_one(panel: EventPanel) -> EventStateRow:
    summaries: list[EventSummary] = []
    for ev in panel.events:
        summaries.append(_summarize(ev, panel.as_of))

    upcoming = [s for s in summaries if s.status == "upcoming"]
    recent = [s for s in summaries if s.status in {"recent", "active"}]
    upcoming.sort(key=lambda s: (s.days_until if s.days_until is not None else 9999, s.event_id))
    recent.sort(key=lambda s: (-(s.days_since or 0), s.event_id))

    days_since = None
    if recent:
        days_since = float(min(s.days_since for s in recent if s.days_since is not None))
    days_until = None
    if upcoming:
        days_until = float(min(s.days_until for s in upcoming if s.days_until is not None))

    # Active set for composite: recent with decay_weight > 0.05 + imminent upcoming
    active = [s for s in recent if s.decay_weight >= 0.05]
    active += [s for s in upcoming if (s.days_until or 999) <= 10]

    if active:
        # ω ∝ decay * importance * confidence proxy
        weights = [max(1e-6, s.decay_weight * s.importance) for s in active]
        wsum = sum(weights)
        composite = sum(w * s.event_score for w, s in zip(weights, active)) / wsum
        impact = sum(w * s.expected_impact for w, s in zip(weights, active)) / wsum
        importance = sum(w * s.importance for w, s in zip(weights, active)) / wsum
        surprise = sum(w * s.surprise_score for w, s in zip(weights, active)) / wsum
        decay = sum(w * s.decay_weight for w, s in zip(weights, active)) / wsum
        primary = max(active, key=lambda s: s.decay_weight * s.importance).event_type
    else:
        composite, impact, importance, surprise, decay, primary = 50.0, 0.0, 0.0, 50.0, 0.0, None

    composite = round(max(0.0, min(100.0, composite)), 6)
    impact = round(max(-100.0, min(100.0, impact)), 6)
    importance = round(max(0.0, min(1.0, importance)), 6)
    surprise = round(surprise, 6)
    decay = round(max(0.0, min(1.0, decay)), 6)

    label, side = _label_side(composite, impact, primary)
    coverage = 1.0 - 0.12 * len(panel.stale)
    conf = round(
        max(
            0.35,
            min(
                0.95,
                0.50
                + 0.20 * importance
                + 0.15 * decay
                + 0.10 * max(0.0, coverage)
                + 0.05 * (1.0 if active else 0.0),
            ),
        ),
        6,
    )
    return EventStateRow(
        symbol=panel.symbol,
        as_of=panel.as_of,
        sector_id=panel.sector_id,
        upcoming_events=upcoming[:10],
        recent_events=recent[:10],
        days_since_event=days_since,
        days_until_event=days_until,
        event_importance=importance,
        surprise_score=surprise,
        decay_factor=decay,
        composite_score=composite,
        expected_event_impact=impact,
        primary_event_type=primary,
        label=label,
        side=side,
        confidence=conf,
        stale_inputs=list(panel.stale),
        discovery=panel.discovery,
        event_meta=dict(panel.event_meta),
    )


def _summarize(ev: PitEvent, as_of: str) -> EventSummary:
    delta = days_delta(as_of, ev.event_time)
    importance = event_importance(ev)
    hl = half_life_for(ev.event_type)
    if delta < 0:
        status = "upcoming"
        days_since = None
        days_until = -delta
        # Upcoming: full pre-event weight only within window
        age_for_decay = 0.0 if -delta <= UPCOMING_WINDOW_DAYS else 999.0
        dw = decay_weight(age_for_decay, hl) if age_for_decay < 900 else 0.0
        if -delta > UPCOMING_WINDOW_DAYS:
            status = "upcoming"
            dw = 0.0
    else:
        days_since = delta
        days_until = None
        dw = decay_weight(float(delta), hl)
        if delta <= 5:
            status = "active"
        elif delta <= RECENT_WINDOW_DAYS:
            status = "recent"
        else:
            status = "recent"
            # keep but near-zero weight beyond window
            if delta > RECENT_WINDOW_DAYS:
                dw = min(dw, 0.02)

    surp = None
    s_score = 50.0
    if ev.event_type in {"earn_q", "earn_fy", "earn_surprise", "eps_surprise", "rev_surprise"}:
        # PIT: only score surprise when event has occurred
        if delta >= 0:
            surp = eps_surprise(ev.actual, ev.consensus)
            s_score = surprise_score_0_100(surp)
        else:
            s_score = 50.0
    elif ev.event_type == "guidance":
        if delta >= 0:
            s_score = guidance_delta_score(ev.guidance_delta)
            surp = ev.guidance_delta
        else:
            s_score = 50.0
    else:
        # Corporate actions: importance-driven catalyst score (neutral surprise)
        s_score = round(50.0 + 40.0 * (importance - 0.5), 6)

    event_score = round(
        max(0.0, min(100.0, 0.55 * s_score + 0.45 * (100.0 * importance))),
        6,
    )
    # Apply decay to intensity contribution
    event_score = round(event_score * max(dw, 0.05 if status == "upcoming" and dw > 0 else dw), 6)
    if status == "upcoming" and dw > 0:
        # Mild pre-event intensity from importance only
        event_score = round(max(0.0, min(100.0, 35.0 + 50.0 * importance)), 6)

    impact = signed_impact(surp, importance) * dw if surp is not None else 0.0
    if ev.event_type in {"rights", "pref_issue"} and delta >= 0:
        impact = -abs(impact) if impact != 0 else -10.0 * importance * dw
    if ev.event_type == "buyback" and delta >= 0:
        impact = abs(impact) if impact != 0 else 15.0 * importance * dw

    return EventSummary(
        event_id=ev.event_id,
        event_type=ev.event_type,
        event_time=ev.event_time,
        status=status,
        days_since=days_since,
        days_until=days_until,
        importance=round(importance, 6),
        surprise=surp,
        surprise_score=s_score,
        decay_halflife_days=hl,
        decay_weight=dw,
        event_score=event_score,
        expected_impact=round(impact, 6),
    )


def _label_side(
    composite: float, impact: float, primary: str | None
) -> tuple[str, str]:
    if primary is None and composite == 50.0:
        return "No Active Catalyst", "neutral"
    if impact >= 15.0 or composite >= 70.0:
        return "Bullish Catalyst", "bullish_catalyst"
    if impact <= -15.0 or composite <= 35.0:
        return "Bearish Catalyst", "bearish_catalyst"
    if abs(impact) < 5.0 and 45.0 <= composite <= 55.0:
        return "Quiet Calendar", "neutral"
    return "Mixed Catalyst", "neutral"
