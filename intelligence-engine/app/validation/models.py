"""Canonical validation contracts — ReplayRun / ReplayResult / reports."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReplayDaySlice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    e01_hash: str | None = None
    e14_hash: str | None = None
    e02_hashes: dict[str, str] = Field(default_factory=dict)
    e13_hashes: dict[str, str] = Field(default_factory=dict)
    e08_hashes: dict[str, str] = Field(default_factory=dict)
    e09_hashes: dict[str, str] = Field(default_factory=dict)
    e04_hashes: dict[str, str] = Field(default_factory=dict)
    e05_hashes: dict[str, str] = Field(default_factory=dict)
    e11_hashes: dict[str, str] = Field(default_factory=dict)
    e03_hashes: dict[str, str] = Field(default_factory=dict)
    l4_hashes: dict[str, str] = Field(default_factory=dict)
    e13_labels: dict[str, str] = Field(default_factory=dict)
    e08_labels: dict[str, str] = Field(default_factory=dict)
    e09_labels: dict[str, str] = Field(default_factory=dict)
    e04_labels: dict[str, str] = Field(default_factory=dict)
    e05_labels: dict[str, str] = Field(default_factory=dict)
    e11_labels: dict[str, str] = Field(default_factory=dict)
    e03_labels: dict[str, str] = Field(default_factory=dict)
    l4_labels: dict[str, str] = Field(default_factory=dict)
    e13_scores: dict[str, float] = Field(default_factory=dict)
    e08_scores: dict[str, float] = Field(default_factory=dict)
    e09_scores: dict[str, float] = Field(default_factory=dict)
    e04_scores: dict[str, float] = Field(default_factory=dict)
    e05_scores: dict[str, float] = Field(default_factory=dict)
    e11_scores: dict[str, float] = Field(default_factory=dict)
    e03_scores: dict[str, float] = Field(default_factory=dict)
    l4_scores: dict[str, float] = Field(default_factory=dict)
    confidences: dict[str, float] = Field(default_factory=dict)
    portfolio_weights: dict[str, float] = Field(default_factory=dict)
    cash_allocation: float = 0.0
    portfolio_hash: str | None = None
    expected_volatility: float | None = None
    e14_risk_level: str | None = None
    e01_regime: str | None = None
    model_versions: dict[str, str] = Field(default_factory=dict)
    formula_versions: dict[str, str] = Field(default_factory=dict)
    portfolio_return: float | None = None
    benchmark_return: float | None = None


class ReplayRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    dataset_id: str
    dataset_version: str
    universe_id: str
    status: str  # pending|running|succeeded|failed
    started_at: str
    finished_at: str | None = None
    n_days: int = 0
    n_symbols: int = 0
    engine_versions: dict[str, str] = Field(default_factory=dict)
    formula_versions: dict[str, str] = Field(default_factory=dict)
    flags: dict[str, bool] = Field(default_factory=dict)
    production_influence: bool = False
    live: bool = False
    error: str | None = None


class PerformanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_returns: list[float] = Field(default_factory=list)
    benchmark_returns: list[float] = Field(default_factory=list)
    cumulative_return: float = 0.0
    benchmark_cumulative_return: float = 0.0
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    turnover: float | None = None
    hit_rate: float | None = None
    win_rate: float | None = None
    information_coefficient: float | None = None
    average_confidence: float | None = None


class CalibrationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buckets: list[dict[str, Any]] = Field(default_factory=list)
    bucket_accuracy: float | None = None
    confidence_calibration_error: float | None = None
    n_observations: int = 0


class ValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    dataset_id: str
    deterministic: bool
    parity_stability: float
    n_days: int
    n_symbols: int
    performance: PerformanceReport
    calibration: CalibrationReport
    engine_versions: dict[str, str] = Field(default_factory=dict)
    formula_versions: dict[str, str] = Field(default_factory=dict)
    production_influence: bool = False
    passed: bool = False
    notes: list[str] = Field(default_factory=list)


class ReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: ReplayRun
    days: list[ReplayDaySlice] = Field(default_factory=list)
    summary: ValidationSummary | None = None
    dashboard: dict[str, Any] = Field(default_factory=dict)
