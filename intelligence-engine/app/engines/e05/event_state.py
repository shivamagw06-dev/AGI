"""Canonical E05EventState contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e05.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e05.models.state import EventStateRow, EventSummary


class EventSummaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    event_time: str
    status: str
    days_since: int | None = None
    days_until: int | None = None
    importance: float
    surprise: float | None = None
    surprise_score: float
    decay_halflife_days: float
    decay_weight: float
    event_score: float
    expected_impact: float


class E05EventState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E05"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    sector_id: str | None = None
    upcoming_events: list[EventSummaryModel] = Field(default_factory=list)
    recent_events: list[EventSummaryModel] = Field(default_factory=list)
    days_since_event: float | None = None
    days_until_event: float | None = None
    event_importance: float
    surprise_score: float
    decay_factor: float
    composite_score: float
    expected_event_impact: float
    primary_event_type: str | None = None
    label: str
    side: str
    confidence: float
    discovery: str = "pit_objects"
    stale_inputs: list[str] = Field(default_factory=list)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    formula_id: str = FORMULA_ID
    model_version: str = MODEL_VERSION
    hash: str = ""


def _sum_model(s: EventSummary) -> EventSummaryModel:
    return EventSummaryModel(
        event_id=s.event_id,
        event_type=s.event_type,
        event_time=s.event_time,
        status=s.status,
        days_since=s.days_since,
        days_until=s.days_until,
        importance=s.importance,
        surprise=s.surprise,
        surprise_score=s.surprise_score,
        decay_halflife_days=s.decay_halflife_days,
        decay_weight=s.decay_weight,
        event_score=s.event_score,
        expected_impact=s.expected_impact,
    )


def e05_from_row(
    row: EventStateRow,
    *,
    universe_id: str,
    e01_ref: dict[str, Any] | None = None,
    e14_ref: dict[str, Any] | None = None,
    digest: str,
) -> E05EventState:
    return E05EventState(
        as_of=row.as_of,
        universe_id=universe_id,
        symbol=row.symbol,
        sector_id=row.sector_id,
        upcoming_events=[_sum_model(s) for s in row.upcoming_events],
        recent_events=[_sum_model(s) for s in row.recent_events],
        days_since_event=row.days_since_event,
        days_until_event=row.days_until_event,
        event_importance=row.event_importance,
        surprise_score=row.surprise_score,
        decay_factor=row.decay_factor,
        composite_score=row.composite_score,
        expected_event_impact=row.expected_event_impact,
        primary_event_type=row.primary_event_type,
        label=row.label,
        side=row.side,
        confidence=row.confidence,
        discovery=row.discovery,
        stale_inputs=row.stale_inputs,
        e01_ref=e01_ref or {},
        e14_ref=e14_ref or {},
        formula_id=FORMULA_ID,
        model_version=MODEL_VERSION,
        hash=digest,
    )
