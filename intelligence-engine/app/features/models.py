"""Feature Registry canonical objects (E00 §6 / WBS FEAT-001)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


QualityFlag = Literal["ok", "stale", "partial", "missing", "error"]


class FeatureMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_id: str
    category: str
    description: str
    owner: str
    formula_version: str
    dependencies: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    refresh_frequency: str
    confidence: float = Field(ge=0, le=1, default=1.0)
    source: str
    unit: str | None = None
    polarity: str | None = None


class FeatureValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_id: str
    formula_version: str
    symbol: str | None = None
    as_of: date | datetime | str
    available_at: datetime
    value: float | int | str | bool | None
    confidence: float = Field(ge=0, le=1, default=1.0)
    quality_flag: QualityFlag = "ok"
    source: str
    input_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeatureSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    as_of: date | datetime | str
    universe_id: str | None = None
    symbol: str | None = None
    values: dict[str, FeatureValue]
    created_at: datetime = Field(default_factory=utcnow)


class HistoricalFeatureSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_id: str
    formula_version: str
    symbol: str | None = None
    points: list[FeatureValue] = Field(default_factory=list)
