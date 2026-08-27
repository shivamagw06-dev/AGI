"""Canonical E11State contract — soft sentiment envelope."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e11.mapping import (
    ENGINE_VERSION,
    FORMULA_ID,
    MODEL_VERSION,
    SOCIAL_WEIGHT_CAP,
    WEIGHT_SET_ID,
)
from app.engines.e11.models.state import SentimentStateRow


class E11State(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E11"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    entity_id: str
    entity_confidence: float
    sector_id: str | None = None
    news_score: float
    composite_score: float
    reliability_weight: float
    decay_weight: float
    freshness_hours: float
    soft_voter_weight: float
    social_weight_cap: float = SOCIAL_WEIGHT_CAP
    social_enabled: bool = False
    doc_count: int = 0
    label: str
    side: str
    confidence: float
    discovery: str = "pit_news"
    stale_inputs: list[str] = Field(default_factory=list)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    weight_set_id: str = WEIGHT_SET_ID
    formula_id: str = FORMULA_ID
    model_version: str = MODEL_VERSION
    hash: str = ""


def e11_from_row(
    row: SentimentStateRow,
    *,
    universe_id: str,
    e01_ref: dict[str, Any] | None = None,
    e14_ref: dict[str, Any] | None = None,
    digest: str,
) -> E11State:
    return E11State(
        as_of=row.as_of,
        universe_id=universe_id,
        symbol=row.symbol,
        entity_id=row.entity_id,
        entity_confidence=row.entity_confidence,
        sector_id=row.sector_id,
        news_score=row.news_score,
        composite_score=row.composite_score,
        reliability_weight=row.reliability_weight,
        decay_weight=row.decay_weight,
        freshness_hours=row.freshness_hours,
        soft_voter_weight=row.soft_voter_weight,
        social_weight_cap=row.social_weight_cap,
        social_enabled=row.social_enabled,
        doc_count=row.doc_count,
        label=row.label,
        side=row.side,
        confidence=row.confidence,
        discovery=row.discovery,
        stale_inputs=row.stale_inputs,
        e01_ref=e01_ref or {},
        e14_ref=e14_ref or {},
        weight_set_id=WEIGHT_SET_ID,
        formula_id=FORMULA_ID,
        model_version=MODEL_VERSION,
        hash=digest,
    )
