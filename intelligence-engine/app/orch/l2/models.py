"""ORCH Layer 2 feature-build contracts (ORCH-003–005)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.features.models import utcnow

BuildStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "timed_out",
    "skipped",
    "suppressed",
]

UpdateType = Literal["ohlcv", "quote", "macro", "fundamentals", "universe", "manual"]


class MarketDataUpdateEvent(BaseModel):
    """Published by MarketDataClient after a successful provider pull."""

    model_config = ConfigDict(extra="forbid")

    update_type: UpdateType
    symbol: str | None = None
    as_of: str
    input_keys: list[str] = Field(default_factory=list)
    payload_fingerprint: str | None = None
    published_at: datetime = Field(default_factory=utcnow)


class FeatureBuildRecord(BaseModel):
    """Every feature build must produce this ledger row."""

    model_config = ConfigDict(extra="forbid")

    build_id: str
    feature_id: str
    formula_version: str
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utcnow)
    duration_ms: float | None = None
    status: BuildStatus
    error: str | None = None
    symbol: str | None = None
    as_of: str
    attempt: int = 1
    batch_id: str | None = None
    orch_run_id: str | None = None


class FeatureReadyEvent(BaseModel):
    """Emitted when a batch finishes — engines may read FeatureSnapshots only."""

    model_config = ConfigDict(extra="forbid")

    batch_id: str
    as_of: str
    symbol: str | None = None
    feature_ids: list[str]
    snapshot_id: str | None = None
    succeeded: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    emitted_at: datetime = Field(default_factory=utcnow)


class BuildBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    symbol: str | None = None
    feature_ids: list[str] | None = None
    update_type: UpdateType = "manual"
    input_keys: list[str] = Field(default_factory=list)
    ctx: dict[str, Any] = Field(default_factory=dict)
    parallel: bool = True
    max_workers: int = 4
