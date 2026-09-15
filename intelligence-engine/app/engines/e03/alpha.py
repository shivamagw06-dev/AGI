"""Canonical E03Alpha contract (spec §9.1, P0/M0 subset)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e03.mapping import ENGINE_VERSION, MODEL_VERSION


class E03Alpha(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "E03"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    sector_id: str | None = None
    agi_tech_score: float
    composite_alpha_score: float
    label: str
    confidence: float
    confidence_pct: int
    technical_score: float | None = None
    momentum_score: float | None = None
    relative_strength_score: float | None = None
    mean_reversion_score: float | None = None
    residual_momentum_score: float | None = None
    probabilities: dict[str, float] = Field(default_factory=dict)
    horizons: dict[str, Any] = Field(default_factory=dict)
    alpha_attribution: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    family_scores: dict[str, float] = Field(default_factory=dict)
    ranks: dict[str, Any] = Field(default_factory=dict)
    e01_ref: dict[str, Any] = Field(default_factory=dict)
    e02_ref: dict[str, Any] = Field(default_factory=dict)
    e14_ref: dict[str, Any] = Field(default_factory=dict)
    e14_projection: dict[str, Any] = Field(default_factory=dict)
    turnover_class: str = "medium"
    capacity_ok: bool = True
    top_features: list[str] = Field(default_factory=list)
    contributions: dict[str, float] = Field(default_factory=dict)
    indicators: dict[str, Any] = Field(default_factory=dict)
    stale_inputs: list[str] = Field(default_factory=list)
    model_version: str = MODEL_VERSION
    submodel_id: str = "SM_AGI_TECH"
    hash: str = ""
