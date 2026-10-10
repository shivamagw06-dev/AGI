"""Canonical E02Exposure contract (spec §9.1, P0 subset)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e02.mapping import ENGINE_VERSION, MODEL_VERSION, P0_FACTORS
from app.engines.e02.models.exposures import FactorExposureRow


class E02Exposure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E02"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    sector_id: str | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    loadings: dict[str, float] = Field(default_factory=dict)
    raw_exposures: dict[str, float] = Field(default_factory=dict)
    factor_features: dict[str, float] = Field(default_factory=dict)
    composite_score: float
    dominant_factor: str
    style_box: dict[str, str] = Field(default_factory=dict)
    factor_confidence: float
    factor_confidence_by_factor: dict[str, float] = Field(default_factory=dict)
    timing_context: dict[str, Any] = Field(default_factory=dict)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    top_metrics: list[dict[str, Any]] = Field(default_factory=list)
    stale_inputs: list[str] = Field(default_factory=list)
    model_version: str = MODEL_VERSION
    hash: str = ""


def exposure_from_row(
    row: FactorExposureRow,
    *,
    universe_id: str,
    e01_ref: dict[str, Any] | None = None,
    e14_ref: dict[str, Any] | None = None,
    digest: str,
) -> E02Exposure:
    # Only P0 factors in public scores/loadings
    scores = {f: row.scores[f] for f in P0_FACTORS if f in row.scores}
    loadings = {f: row.loadings[f] for f in P0_FACTORS if f in row.loadings}
    return E02Exposure(
        as_of=row.as_of,
        universe_id=universe_id,
        symbol=row.symbol,
        sector_id=row.sector_id,
        scores=scores,
        loadings=loadings,
        raw_exposures=row.raw_factor_z,
        factor_features=row.factor_features,
        composite_score=row.composite_score,
        dominant_factor=row.dominant_factor if row.dominant_factor in scores else next(iter(scores), "F_QUALITY"),
        style_box=row.style_box,
        factor_confidence=row.overall_confidence,
        factor_confidence_by_factor=row.factor_confidence,
        timing_context={
            "e01_primary_regime": (e01_ref or {}).get("primary_regime"),
            "timing_weight_hint": {},  # E02_TIMING=false
        },
        e01_ref=e01_ref or {},
        e14_ref=e14_ref or {},
        top_metrics=row.top_metrics,
        stale_inputs=row.stale_inputs,
        model_version=MODEL_VERSION,
        hash=digest,
    )
