"""Canonical E04State contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e04.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e04.models.state import RelativeValueRow


class E04State(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E04"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    pair_id: str
    leg_a: str
    leg_b: str
    sector_id: str | None = None
    hedge_alpha: float
    hedge_beta: float
    r_squared: float
    spread: float
    z_score: float
    cointegrated: bool
    adf_stat: float
    half_life: float | None = None
    mispricing_score: float
    mean_reversion_signal: float
    composite_score: float
    label: str
    side: str
    confidence: float
    discovery: str = "static"
    stale_inputs: list[str] = Field(default_factory=list)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    e02_ref: dict[str, Any] = Field(default_factory=dict)
    e03_ref: dict[str, Any] = Field(default_factory=dict)
    formula_id: str = FORMULA_ID
    model_version: str = MODEL_VERSION
    hash: str = ""


def e04_from_row(
    row: RelativeValueRow,
    *,
    universe_id: str,
    e01_ref: dict[str, Any] | None = None,
    e14_ref: dict[str, Any] | None = None,
    e02_ref: dict[str, Any] | None = None,
    e03_ref: dict[str, Any] | None = None,
    digest: str,
) -> E04State:
    return E04State(
        as_of=row.as_of,
        universe_id=universe_id,
        pair_id=row.pair_id,
        leg_a=row.leg_a,
        leg_b=row.leg_b,
        sector_id=row.sector_id,
        hedge_alpha=row.hedge_alpha,
        hedge_beta=row.hedge_beta,
        r_squared=row.r_squared,
        spread=row.spread,
        z_score=row.z_score,
        cointegrated=row.cointegrated,
        adf_stat=row.adf_stat,
        half_life=row.half_life,
        mispricing_score=row.mispricing_score,
        mean_reversion_signal=row.mean_reversion_signal,
        composite_score=row.composite_score,
        label=row.label,
        side=row.side,
        confidence=row.confidence,
        discovery=row.discovery,
        stale_inputs=row.stale_inputs,
        e01_ref=e01_ref or {},
        e14_ref=e14_ref or {},
        e02_ref=e02_ref or {},
        e03_ref=e03_ref or {},
        formula_id=FORMULA_ID,
        model_version=MODEL_VERSION,
        hash=digest,
    )
