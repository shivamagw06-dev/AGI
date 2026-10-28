"""CRE canonical outputs — scorecards, alerts, promotion evidence."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ROLLING_WINDOWS = (30, 90, 252)


class RollingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window: int
    days_used: int
    information_coefficient: float | None = None
    calibration_error: float | None = None
    brier_score: float | None = None
    precision: float | None = None
    recall: float | None = None
    hit_rate: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    turnover: float | None = None
    average_confidence: float | None = None
    latency_ms: float | None = None
    schema_stability: float | None = None
    parity_stability: float | None = None


class EngineScorecard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str
    as_of: str
    model_version: str | None = None
    formula_versions: dict[str, str] = Field(default_factory=dict)
    rolling: dict[str, RollingMetrics] = Field(default_factory=dict)
    rank_score: float = 0.0
    status: str = "ok"  # ok|watch|degraded
    notes: list[str] = Field(default_factory=list)


class CompositeScorecard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    engines: list[str] = Field(default_factory=list)
    ranking: list[dict[str, Any]] = Field(default_factory=list)
    overall_status: str = "ok"
    parity_stability: float | None = None
    schema_stability: float | None = None
    promotion_ready: bool = False
    notes: list[str] = Field(default_factory=list)


class DriftAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    kind: str  # model|confidence|feature|distribution|performance
    engine: str
    severity: str  # info|watch|critical
    metric: str
    baseline: float | None = None
    current: float | None = None
    delta: float | None = None
    message: str
    as_of: str
    timestamp: str


class RegressionAlert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    engine: str
    severity: str
    metric: str
    baseline: float | None = None
    current: float | None = None
    message: str
    as_of: str
    timestamp: str


class PromotionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    engine: str | None = None
    promotion_flag: bool = False
    evidence_only: bool = True
    ready: bool = False
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    engine_versions: dict[str, str] = Field(default_factory=dict)
    formula_versions: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class CREEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_id: str
    as_of: str
    dataset_id: str
    started_at: str
    finished_at: str
    replay_run_id: str | None = None
    engine_scorecards: list[EngineScorecard] = Field(default_factory=list)
    composite: CompositeScorecard | None = None
    drift_alerts: list[DriftAlert] = Field(default_factory=list)
    regression_alerts: list[RegressionAlert] = Field(default_factory=list)
    promotion: PromotionReport | None = None
    dashboard: dict[str, Any] = Field(default_factory=dict)
    production_influence: bool = False
    flags: dict[str, bool] = Field(default_factory=dict)
