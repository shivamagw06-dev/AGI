"""Canonical E09State contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e09.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e09.models.state import TrendStateRow


class E09State(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E09"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    sector_id: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    short_trend: float
    medium_trend: float
    long_trend: float
    ts_momentum: float
    vol_scaled_signal: float
    persistence: float
    exhaustion: float
    composite_score: float
    side: str
    label: str
    confidence: float
    stale_inputs: list[str] = Field(default_factory=list)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    formula_id: str = FORMULA_ID
    model_version: str = MODEL_VERSION
    hash: str = ""


def e09_from_row(
    row: TrendStateRow,
    *,
    universe_id: str,
    e01_ref: dict[str, Any] | None = None,
    e14_ref: dict[str, Any] | None = None,
    digest: str,
) -> E09State:
    return E09State(
        as_of=row.as_of,
        universe_id=universe_id,
        symbol=row.symbol,
        sector_id=row.sector_id,
        metrics=row.metrics,
        short_trend=row.short_trend,
        medium_trend=row.medium_trend,
        long_trend=row.long_trend,
        ts_momentum=row.ts_momentum,
        vol_scaled_signal=row.vol_scaled_signal,
        persistence=row.persistence,
        exhaustion=row.exhaustion,
        composite_score=row.composite_score,
        side=row.side,
        label=row.label,
        confidence=row.confidence,
        stale_inputs=row.stale_inputs,
        e01_ref=e01_ref or {},
        e14_ref=e14_ref or {},
        formula_id=FORMULA_ID,
        model_version=MODEL_VERSION,
        hash=digest,
    )
