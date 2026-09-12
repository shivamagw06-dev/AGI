"""FLE domain models — immutable, versioned forecast institutional memory."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def new_id(prefix: str) -> str:
    return _id(prefix)


def now_iso() -> str:
    return _now()


@dataclass
class Explainability:
    why: str = ""
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    alternative_scenarios: list[str] = field(default_factory=list)
    historical_similar_cases: list[str] = field(default_factory=list)
    expected_timeline: str = ""
    confidence: float = 0.0
    last_updated: str = field(default_factory=_now)
    responsible_engine: str = "fle"
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioCase:
    case_type: str  # bull | base | bear
    probability: float = 0.33
    expected_outcome: str = ""
    drivers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    confidence: float = 0.0
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastRecord:
    """Immutable forecast object — never overwrite; new versions append."""

    forecast_id: str
    company_id: str = ""
    company_symbol: str = ""
    sector_id: str = ""
    theme_ids: list[str] = field(default_factory=list)
    forecast_type: str = "company"  # category
    metric: str = ""
    predicted_value: str = ""
    predicted_numeric: float | None = None
    direction: str = ""  # up | down | flat | range
    unit: str = ""
    horizon_days: int = 90
    created_at: str = field(default_factory=_now)
    review_date: str | None = None
    expected_resolution: str | None = None
    status: str = "active"
    version: int = 1
    owner_engine: str = "fle"
    origin: str = "user_request"
    evidence_ids: list[str] = field(default_factory=list)
    evidence_links: list[dict[str, Any]] = field(default_factory=list)
    knowledge_object_ids: list[str] = field(default_factory=list)
    thesis_id: str = ""
    dna_refs: list[str] = field(default_factory=list)
    risk_ids: list[str] = field(default_factory=list)
    catalyst_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    probability: float = 0.5
    priority: str = "normal"
    tags: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    bull: ScenarioCase = field(default_factory=lambda: ScenarioCase(case_type="bull", probability=0.25))
    base: ScenarioCase = field(default_factory=lambda: ScenarioCase(case_type="base", probability=0.5))
    bear: ScenarioCase = field(default_factory=lambda: ScenarioCase(case_type="bear", probability=0.25))
    explainability: Explainability = field(default_factory=Explainability)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    parent_forecast_id: str = ""  # prior version link
    soft_deleted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "company_id": self.company_id,
            "company_symbol": self.company_symbol,
            "sector_id": self.sector_id,
            "theme_ids": list(self.theme_ids),
            "forecast_type": self.forecast_type,
            "metric": self.metric,
            "predicted_value": self.predicted_value,
            "predicted_numeric": self.predicted_numeric,
            "direction": self.direction,
            "unit": self.unit,
            "horizon_days": self.horizon_days,
            "created_at": self.created_at,
            "review_date": self.review_date,
            "expected_resolution": self.expected_resolution,
            "status": self.status,
            "version": self.version,
            "owner_engine": self.owner_engine,
            "origin": self.origin,
            "evidence_ids": list(self.evidence_ids),
            "evidence_links": list(self.evidence_links),
            "knowledge_object_ids": list(self.knowledge_object_ids),
            "thesis_id": self.thesis_id,
            "dna_refs": list(self.dna_refs),
            "risk_ids": list(self.risk_ids),
            "catalyst_ids": list(self.catalyst_ids),
            "confidence": self.confidence,
            "probability": self.probability,
            "priority": self.priority,
            "tags": list(self.tags),
            "assumptions": list(self.assumptions),
            "bull": self.bull.to_dict(),
            "base": self.base.to_dict(),
            "bear": self.bear.to_dict(),
            "explainability": self.explainability.to_dict(),
            "relationships": list(self.relationships),
            "parent_forecast_id": self.parent_forecast_id,
            "soft_deleted": self.soft_deleted,
        }


@dataclass
class OutcomeRecord:
    outcome_id: str
    forecast_id: str
    predicted_value: str = ""
    predicted_numeric: float | None = None
    actual_value: str = ""
    actual_numeric: float | None = None
    difference: float | None = None
    percentage_error: float | None = None
    absolute_error: float | None = None
    direction_correct: bool | None = None
    magnitude_ok: bool | None = None
    timing_ok: bool | None = None
    accuracy_score: float = 0.0
    error_reason: str = ""
    resolution_date: str = field(default_factory=_now)
    resolver: str = "fle.resolution"
    evidence_ids: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearningRecord:
    learning_id: str
    forecast_id: str
    outcome_id: str = ""
    company_id: str = ""
    sector_id: str = ""
    metric: str = ""
    lessons_learned: list[str] = field(default_factory=list)
    successful_drivers: list[str] = field(default_factory=list)
    failed_assumptions: list[str] = field(default_factory=list)
    unexpected_events: list[str] = field(default_factory=list)
    confidence_adjustments: dict[str, Any] = field(default_factory=dict)
    knowledge_updates: list[str] = field(default_factory=list)
    future_improvements: list[str] = field(default_factory=list)
    searchable_text: str = ""
    created_at: str = field(default_factory=_now)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CalibrationBucket:
    band: str
    predicted_confidence_low: float
    predicted_confidence_high: float
    forecast_count: int = 0
    success_count: int = 0
    historical_success_rate: float = 0.0
    calibration_label: str = "unknown"  # well_calibrated | overconfident | underconfident
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CalibrationSnapshot:
    snapshot_id: str
    scope: str  # global | sector | company | metric
    scope_id: str = ""
    buckets: list[CalibrationBucket] = field(default_factory=list)
    average_confidence: float = 0.0
    average_success: float = 0.0
    calibration_drift: float = 0.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "scope": self.scope,
            "scope_id": self.scope_id,
            "buckets": [b.to_dict() for b in self.buckets],
            "average_confidence": self.average_confidence,
            "average_success": self.average_success,
            "calibration_drift": self.calibration_drift,
            "created_at": self.created_at,
        }


@dataclass
class AccuracySummary:
    scope: str
    scope_id: str
    forecast_count: int = 0
    resolved_count: int = 0
    directional_accuracy: float = 0.0
    mean_percentage_error: float = 0.0
    mean_absolute_error: float = 0.0
    mean_accuracy_score: float = 0.0
    confidence_accuracy: float = 0.0
    by_horizon: dict[str, float] = field(default_factory=dict)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastHealth:
    company_id: str
    forecast_coverage: int = 0
    forecast_accuracy: float = 0.0
    pending_reviews: int = 0
    expired_forecasts: int = 0
    average_confidence: float = 0.0
    calibration_label: str = "unknown"
    learning_score: float = 0.0
    forecast_freshness: str = ""
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RelationshipEdge:
    edge_id: str
    from_id: str
    to_id: str
    relation_type: str
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEntry:
    action: str
    object_kind: str = ""
    object_id: str = ""
    detail: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
