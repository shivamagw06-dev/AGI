"""Immutable, provider-independent CRE contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


CRE_VERSION = "cre-v1.0.0"

EPISTEMIC_LABELS = (
    "FACT", "OBSERVATION", "CALCULATION", "SCENARIO", "FORECAST",
    "CAUSAL_INTERPRETATION", "HYPOTHESIS", "THESIS", "OPINION",
)
RELATIONSHIP_TYPES = (
    "DIRECT", "INDIRECT", "CONDITIONAL", "FEEDBACK", "CORRELATIONAL",
    "CAUSAL_HYPOTHESIS", "STRUCTURAL", "TEMPORAL", "COMPETITIVE",
    "REGULATORY", "MACRO_TRANSMISSION", "FINANCIAL_TRANSMISSION",
)
DIRECTIONS = ("POSITIVE", "NEGATIVE", "MIXED", "NON_LINEAR", "CONDITIONAL", "UNKNOWN")
STRENGTHS = ("VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH", "UNKNOWN")
TIME_LAGS = (
    "IMMEDIATE", "DAYS", "WEEKS", "MONTHS", "1_QUARTER", "2_QUARTERS",
    "3_QUARTERS", "4_QUARTERS", "MULTI_YEAR", "UNKNOWN",
)
KNOWLEDGE_STATUSES = ("PROPOSED", "VALIDATED", "TRUSTED", "QUARANTINED", "REJECTED", "EXPIRED", "SUPERSEDED")
CONTRADICTION_STATUSES = ("RESOLVED", "PARTIALLY_RESOLVED", "UNRESOLVED", "INSUFFICIENT_EVIDENCE")
SCENARIOS = ("BEAR", "BASE", "BULL", "CUSTOM")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    source_type: str
    source_id: str
    source_date: str | None = None
    publication_date: str | None = None
    available_at: str | None = None
    passage: str | None = None
    authority_rank: int | None = None
    primary_source_id: str | None = None
    secondary_source_ids: tuple[str, ...] = ()
    quality: str = "UNVALIDATED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CounterEffect:
    effect: str
    direction: str
    mechanism: str
    time_lag: str = "UNKNOWN"
    conditions: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CausalRelationship:
    relationship_id: str
    cause: str
    effect: str
    direction: str
    relationship_type: str
    epistemic_label: str
    industry: str | None = None
    sub_industry: str | None = None
    company_id: str | None = None
    segment: str | None = None
    generalization_scope: str = "GENERAL"
    strength: str = "UNKNOWN"
    confidence: float = 0.0
    time_lag: str = "UNKNOWN"
    conditions: tuple[str, ...] = ()
    counter_effects: tuple[CounterEffect, ...] = ()
    mechanism: str = ""
    expected_frequency: str | None = None
    evidence: tuple[EvidenceReference, ...] = ()
    source_count: int = 0
    source_quality: str = "UNVALIDATED"
    valid_from: str | None = None
    valid_to: str | None = None
    observed_period: str | None = None
    market_regime: str | None = None
    industry_regime: str | None = None
    regulatory_regime: str | None = None
    status: str = "PROPOSED"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    version: str = CRE_VERSION
    parent_relationship_id: str | None = None
    created_by: str = "system"
    fabricated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContradictionGroup:
    contradiction_id: str
    relationship_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    company_id: str | None = None
    industry: str | None = None
    period: str | None = None
    severity: str = "MEDIUM"
    resolution: str | None = None
    status: str = "UNRESOLVED"
    created_at: str = field(default_factory=_now)
    version: str = CRE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinancialImpact:
    impact_id: str
    company_id: str
    event_id: str
    metric: str
    direction: str
    epistemic_label: str
    estimated_change: float | None = None
    unit: str | None = None
    period: str | None = None
    scenario: str | None = None
    calculation_id: str | None = None
    afe_result: dict[str, Any] | None = None
    assumptions: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    status: str = "PROPOSED"
    analysis_as_of: str | None = None
    created_at: str = field(default_factory=_now)
    version: str = CRE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CausalEvent:
    event_id: str
    title: str
    event_type: str
    occurred_at: str
    available_at: str
    company_id: str | None = None
    industry: str | None = None
    claims: tuple[str, ...] = ()
    evidence: tuple[EvidenceReference, ...] = ()
    status: str = "PROPOSED"
    version: str = CRE_VERSION


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    name: str
    probability: float
    relationship_ids: tuple[str, ...]
    financial_impact_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    valuation_effect: str = "UNKNOWN"
    epistemic_label: str = "SCENARIO"
    status: str = "PROPOSED"
    version: str = CRE_VERSION


@dataclass(frozen=True)
class ThesisUpdateProposal:
    proposal_id: str
    thesis_id: str
    relationship_ids: tuple[str, ...]
    impact_ids: tuple[str, ...]
    direction: str
    rationale: str
    invalidation_conditions: tuple[str, ...] = ()
    monitoring_indicators: tuple[str, ...] = ()
    status: str = "PROPOSED"
    version: str = CRE_VERSION


@dataclass(frozen=True)
class OutcomeRecord:
    outcome_id: str
    relationship_id: str
    expected_direction: str
    observed_direction: str
    observation_date: str
    evidence_ids: tuple[str, ...]
    matched: bool
    confidence_delta: float
    status: str = "PROPOSED"
    version: str = CRE_VERSION
