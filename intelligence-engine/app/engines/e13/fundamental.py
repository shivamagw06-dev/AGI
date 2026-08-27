"""Canonical E13Fundamental contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e13.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e13.models.scorer import FundamentalScoreRow


class E13Fundamental(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E13"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    sector_id: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    quality_score: float
    value_score: float
    growth_score: float
    balance_sheet_score: float
    pillar_scores: dict[str, float] = Field(default_factory=dict)
    composite_score: float
    label: str
    side: str
    confidence: float
    top_metrics: list[dict[str, Any]] = Field(default_factory=list)
    stale_inputs: list[str] = Field(default_factory=list)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    formula_id: str = FORMULA_ID
    model_version: str = MODEL_VERSION
    hash: str = ""


def fundamental_from_row(
    row: FundamentalScoreRow,
    *,
    universe_id: str,
    e01_ref: dict[str, Any] | None = None,
    e14_ref: dict[str, Any] | None = None,
    digest: str,
) -> E13Fundamental:
    return E13Fundamental(
        as_of=row.as_of,
        universe_id=universe_id,
        symbol=row.symbol,
        sector_id=row.sector_id,
        metrics=row.metrics,
        quality_score=row.quality_score,
        value_score=row.value_score,
        growth_score=row.growth_score,
        balance_sheet_score=row.balance_sheet_score,
        pillar_scores=row.pillar_scores,
        composite_score=row.composite_score,
        label=row.label,
        side=row.side,
        confidence=row.confidence,
        top_metrics=row.top_metrics,
        stale_inputs=row.stale_inputs,
        e01_ref=e01_ref or {},
        e14_ref=e14_ref or {},
        formula_id=FORMULA_ID,
        model_version=MODEL_VERSION,
        hash=digest,
    )
