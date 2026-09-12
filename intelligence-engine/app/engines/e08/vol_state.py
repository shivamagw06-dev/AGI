"""Canonical E08State contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e08.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e08.models.state import VolatilityStateRow


class E08State(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E08"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    sector_id: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    realized_vol: float
    historical_vol: float
    vol_regime: str
    expansion: bool
    compression: bool
    expansion_score: float
    compression_score: float
    expected_move: float | None = None
    composite_score: float
    label: str
    confidence: float
    stale_inputs: list[str] = Field(default_factory=list)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    formula_id: str = FORMULA_ID
    model_version: str = MODEL_VERSION
    hash: str = ""


def e08_from_row(
    row: VolatilityStateRow,
    *,
    universe_id: str,
    e01_ref: dict[str, Any] | None = None,
    e14_ref: dict[str, Any] | None = None,
    digest: str,
) -> E08State:
    return E08State(
        as_of=row.as_of,
        universe_id=universe_id,
        symbol=row.symbol,
        sector_id=row.sector_id,
        metrics=row.metrics,
        realized_vol=row.realized_vol,
        historical_vol=row.historical_vol,
        vol_regime=row.vol_regime,
        expansion=row.expansion,
        compression=row.compression,
        expansion_score=row.expansion_score,
        compression_score=row.compression_score,
        expected_move=row.expected_move,
        composite_score=row.composite_score,
        label=row.label,
        confidence=row.confidence,
        stale_inputs=row.stale_inputs,
        e01_ref=e01_ref or {},
        e14_ref=e14_ref or {},
        formula_id=FORMULA_ID,
        model_version=MODEL_VERSION,
        hash=digest,
    )
