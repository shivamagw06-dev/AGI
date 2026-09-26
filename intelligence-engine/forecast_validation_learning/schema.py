"""FVL contracts — Forecast Validation & Learning (Sprint 9.5).

History is never rewritten. Validation and learning are append-only records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

FVL_VERSION = "0.1.0"
PROGRAMME = "Forecast Validation & Learning"
PROGRAMME_SHORT = "FVL"
PRIMARY_QUESTION = "Were we right?"

NO_FVL_ACTIONS = (
    "rewrite_historical_forecasts",
    "mutate_assessment_snapshots",
    "predict_stock_prices",
    "recommend_buy_sell",
    "set_target_prices",
    "execute_trades",
    "call_live_market_providers",
)

ValidationStatus = Literal[
    "Pending",
    "Monitoring",
    "Validated",
    "Partially Correct",
    "Incorrect",
    "Indeterminate",
]

LEARNING_CATEGORIES: tuple[str, ...] = (
    "Company forecasting",
    "Sector forecasting",
    "Market forecasting",
    "Macro forecasting",
    "Catalyst effectiveness",
    "Scenario quality",
    "Probability calibration",
    "Confidence calibration",
)

TERMINAL_STATUSES = frozenset(
    {"Validated", "Partially Correct", "Incorrect", "Indeterminate"}
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "fvl") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ExpectedOutcome(BaseModel):
    """Snapshot of what the forecast implied — frozen at registration."""

    modal_scenario: str  # Bull | Base | Bear
    probability_distribution: dict[str, int] = Field(default_factory=dict)
    confidence_pct: int = 0
    growth_direction: str = "stable"  # up | down | stable
    margin_direction: str = "stable"
    catalysts: list[str] = Field(default_factory=list)
    timing_horizon: str = "medium"
    narrative_summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)


class ActualOutcome(BaseModel):
    """Observed reality — never used to edit the registered forecast."""

    realized_scenario: str  # Bull | Base | Bear | Unknown
    growth_direction: str = "stable"
    margin_direction: str = "stable"
    catalysts_materialized: list[str] = Field(default_factory=list)
    timing_realized: str = "on_time"  # early | on_time | late | unknown
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    source: str = "agi_seeded_outcome"
    observed_at: datetime = Field(default_factory=utc_now)
    notes: str = ""


class OutcomeDifference(BaseModel):
    scenario_match: bool = False
    scenario_distance: int = 0  # 0 same, 1 adjacent, 2 opposite
    growth_match: bool = False
    margin_match: bool = False
    catalyst_hit_rate: float = 0.0
    timing_match: bool = False
    metric_agreement_pct: float = 0.0
    summary: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class RegisteredForecast(BaseModel):
    """Immutable, versioned forecast registry entry (publication gate)."""

    forecast_id: str = Field(default_factory=lambda: new_id("fcst"))
    version: int = 1
    parent_forecast_id: str | None = None
    entity: str
    entity_label: str | None = None
    scope: str = "company"
    forecast_date: datetime = Field(default_factory=utc_now)
    assessment_id: str | None = None
    scenario_report_id: str | None = None
    forecast_bundle_id: str | None = None
    assessment_snapshot: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: ExpectedOutcome
    status: ValidationStatus = "Pending"
    published: bool = True
    published_at: datetime = Field(default_factory=utc_now)
    providers_queried: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    note: str = (
        "Immutable registry snapshot. Status transitions are recorded via validations; "
        "this snapshot body is never rewritten."
    )

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["immutable"] = True
        data["history_rewritten"] = False
        return data


class ForecastValidation(BaseModel):
    """Immutable validation record — append-only evaluation of a forecast."""

    validation_id: str = Field(default_factory=lambda: new_id("fval"))
    forecast_id: str
    entity: str
    scope: str = "company"
    forecast_date: datetime | None = None
    validation_date: datetime = Field(default_factory=utc_now)
    expected_outcome: ExpectedOutcome
    actual_outcome: ActualOutcome
    difference: OutcomeDifference
    validation_status: ValidationStatus
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: int = 0
    score: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    history_rewritten: bool = False
    version: str = FVL_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["primary_question"] = PRIMARY_QUESTION
        data["does_not"] = list(NO_FVL_ACTIONS)
        data["immutable"] = True
        return data


class ForecastScore(BaseModel):
    overall: int
    scenario_accuracy: int
    probability_calibration: int
    catalyst_accuracy: int
    timing_accuracy: int
    confidence_calibration: int
    components: dict[str, Any] = Field(default_factory=dict)


class InvestmentLearning(BaseModel):
    """New learning object — never edits the historical forecast."""

    learning_id: str = Field(default_factory=lambda: new_id("learn"))
    topic: str
    observation: str
    learning: str
    future_guidance: str
    category: str
    forecast_id: str | None = None
    validation_id: str | None = None
    entity: str | None = None
    scope: str | None = None
    outcome_status: ValidationStatus | None = None
    bias_flags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    history_rewritten: bool = False
    knowledge_factory_updated: bool = False
    process_memory: bool = True
    version: str = FVL_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        return data


class BiasIndicator(BaseModel):
    code: str
    label: str
    severity: str  # low | moderate | high
    evidence_count: int = 0
    detail: str = ""
    recommendation: str = ""


class CalibrationPoint(BaseModel):
    bucket: str
    predicted_pct: float
    occurred_pct: float
    n: int
    gap_pct: float
    note: str = ""
