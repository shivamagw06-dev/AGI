"""Canonical L4Opinion contract (P0 Shadow subset)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.l4.mapping import ENGINE_VERSION, MODEL_VERSION, WEIGHT_SET_ID


class L4Opinion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = "L4"
    version: str = ENGINE_VERSION
    as_of: str
    universe_id: str
    symbol: str
    object_type: str = "symbol"
    label: str
    composite_score: float
    confidence: float
    positive_evidence: list[dict[str, Any]] = Field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    unknowns: list[dict[str, Any]] = Field(default_factory=list)
    dominant_drivers: list[dict[str, Any]] = Field(default_factory=list)
    explanation: dict[str, Any] = Field(default_factory=dict)
    engine_contributions: list[dict[str, Any]] = Field(default_factory=list)
    hierarchy_trace: list[str] = Field(default_factory=list)
    conflict_resolution: str = "none"
    confidence_mult: float = 1.0
    e14_gate: str | None = None
    weight_set_id: str = WEIGHT_SET_ID
    shadow: bool = True
    primary: bool = False
    upstream_hashes: dict[str, str] = Field(default_factory=dict)
    stale_inputs: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    model_version: str = MODEL_VERSION
    hash: str = ""
