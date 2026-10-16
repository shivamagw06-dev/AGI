"""AIP canonical contracts — weight sets, experiments, contribution, reports."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.aip.roadmap import AIP_VERSION


class MetricBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sharpe: float | None = None
    sortino: float | None = None
    information_coefficient: float | None = None
    hit_rate: float | None = None
    calibration_error: float | None = None
    max_drawdown: float | None = None
    turnover: float | None = None
    prediction_accuracy: float | None = None
    n_observations: int = 0
    n_days: int = 0


class MetricDeltas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sharpe_delta: float | None = None
    sortino_delta: float | None = None
    ic_delta: float | None = None
    hit_rate_delta: float | None = None
    calibration_delta: float | None = None
    max_drawdown_delta: float | None = None
    turnover_delta: float | None = None
    prediction_accuracy_delta: float | None = None


class WeightSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight_set_id: str
    name: str
    description: str = ""
    weights: dict[str, float] = Field(default_factory=dict)
    regime: str | None = None
    sector: str | None = None
    baseline: bool = False
    shadow_only: bool = True
    production: bool = False
    parent_weight_set_id: str | None = None
    created_at: str | None = None
    notes: list[str] = Field(default_factory=list)


class EngineContribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str
    baseline_weight: float
    alpha_delta: float | None = None
    sharpe_delta: float | None = None
    sortino_delta: float | None = None
    max_drawdown_delta: float | None = None
    ic_delta: float | None = None
    hit_rate_delta: float | None = None
    calibration_delta: float | None = None
    marginal_information_gain: float | None = None
    recommend_larger_weight: bool = False
    recommend_smaller_weight: bool = False
    notes: list[str] = Field(default_factory=list)


class ContributionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    as_of: str
    dataset_id: str
    weight_set_id: str
    engines: list[EngineContribution] = Field(default_factory=list)
    production_influence: bool = False


class CalibrationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    as_of: str
    dataset_id: str
    baseline_calibration_error: float | None = None
    proposed_calibration_error: float | None = None
    temperature: float | None = None
    bucket_map: list[dict[str, Any]] = Field(default_factory=list)
    applied_to_production: bool = False
    notes: list[str] = Field(default_factory=list)


class PredictionAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    symbol: str
    score: float
    label: str
    confidence: float
    engine_shares: dict[str, float] = Field(default_factory=dict)
    dominant_engine: str | None = None
    forward_return: float | None = None
    correct: bool | None = None


class AttributionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    dataset_id: str
    weight_set_id: str
    rows: list[PredictionAttribution] = Field(default_factory=list)
    production_influence: bool = False


class HouseViewEvolutionPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    label: str
    score: float
    confidence: float
    changed: bool = False
    prior_label: str | None = None


class HouseViewEvolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    points: list[HouseViewEvolutionPoint] = Field(default_factory=list)
    n_changes: int = 0
    source: str = "replay_l4_shadow"


class QualityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str  # research|client_answer
    score: float
    components: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ExperimentHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str
    workstream: str
    expected_effect: str


class SignificanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = "paired_bootstrap_ic"
    n_bootstrap: int = 0
    p_value: float | None = None
    significant: bool = False
    alpha: float = 0.05
    detail: str = ""


class RollbackPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rollback_to_weight_set_id: str
    automatic: bool = True
    production_touched: bool = False
    notes: list[str] = Field(default_factory=list)


class BaselineComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline: str
    metrics: MetricBundle
    deltas: MetricDeltas


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis: ExperimentHypothesis
    candidate_weight_set_id: str | None = None
    candidate_weights: dict[str, float] | None = None
    dataset_id: str = "golden_p0_v1"
    regime: str | None = None
    sector: str | None = None
    name: str | None = None


class ExperimentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    name: str
    workstream: str
    hypothesis: ExperimentHypothesis
    dataset_id: str
    as_of: str
    started_at: str
    finished_at: str
    replay_run_id: str | None = None
    cre_evaluation_id: str | None = None
    baseline_weight_set_id: str
    candidate_weight_set_id: str
    candidate_metrics: MetricBundle
    comparisons: list[BaselineComparison] = Field(default_factory=list)
    contribution: ContributionReport | None = None
    calibration: CalibrationPlan | None = None
    attribution: AttributionReport | None = None
    significance: SignificanceResult
    rollback: RollbackPlan
    promotion_ready: bool = False
    production_influence: bool = False
    l4_remains_shadow: bool = True
    flags: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    aip_version: str = AIP_VERSION


class PromotionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    experiment_id: str | None = None
    promotion_flag: bool = False
    evidence_only: bool = True
    ready: bool = False
    checklist: list[dict[str, Any]] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AipDashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programme: str = "Alpha Improvement Programme"
    version: str = AIP_VERSION
    architecture_status: str = "v1.0.1 LOCKED"
    l4_shadow: bool = True
    production_influence: bool = False
    n_weight_sets: int = 0
    n_experiments: int = 0
    latest_experiment_id: str | None = None
    promotion_ready: bool = False
    workstreams: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
