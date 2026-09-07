"""Historical Acquisition Platform contracts — raw archive + historical knowledge objects."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Source(str, Enum):
    YAHOO = "yahoo"
    NSE = "nse"
    BSE = "bse"
    COMPANY_IR = "company_ir"
    DERIVED = "derived"


class HistoricalObjectType(str, Enum):
    PRICE_HISTORY = "HistoricalPriceHistory"
    # Sprint 8.2 canonical alias used in HKO views
    PRICE = "HistoricalPrice"
    FINANCIAL_STATEMENT = "HistoricalFinancialStatement"
    BALANCE_SHEET = "HistoricalBalanceSheet"
    CASH_FLOW = "HistoricalCashFlow"
    CORPORATE_EVENT = "HistoricalCorporateEvent"
    CORPORATE_ACTION = "HistoricalCorporateAction"
    DIVIDEND_HISTORY = "HistoricalDividendHistory"
    OWNERSHIP_HISTORY = "HistoricalOwnershipHistory"
    MARKET_SNAPSHOT = "HistoricalMarketSnapshot"
    COMPANY_PROFILE = "HistoricalCompanyProfile"
    NEWS_EVENT = "HistoricalNewsEvent"
    TIMELINE_EVENT = "HistoricalTimelineEvent"


class TimelineScope(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MARKET = "market"
    MACRO = "macro"


class TimelineImportance(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ValidationStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


class PeriodKind(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    EVENT = "event"
    POINT_IN_TIME = "point_in_time"


class RawHistoricalEvent(BaseModel):
    """Append-only raw archive unit — never mutated after insert."""

    event_id: str = Field(default_factory=new_id)
    source: Source
    collector_id: str
    endpoint: str
    company_symbol: str | None = None
    category: str
    payload: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=utc_now)
    effective_start: str | None = None  # ISO date or period label
    effective_end: str | None = None
    checksum: str
    validation_status: ValidationStatus | None = None
    validation_errors: list[str] = Field(default_factory=list)
    ingestion_run_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class EntityRefs(BaseModel):
    company_symbol: str | None = None
    company_name: str | None = None
    sector: str | None = None
    sector_key: str | None = None
    industry: str | None = None
    index_membership: list[str] = Field(default_factory=list)
    time_period: str | None = None  # e.g. FY2019 Q3
    period_kind: PeriodKind | None = None


class HistoricalProvenance(BaseModel):
    source: Source
    collector_id: str | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)
    effective_date: str | None = None
    version: int = 1
    checksum: str | None = None
    source_event_ids: list[str] = Field(default_factory=list)
    ingestion_run_id: str | None = None


class HistoricalKnowledgeObject(BaseModel):
    """Canonical historical object — append-only versions."""

    object_type: HistoricalObjectType
    object_id: str = Field(default_factory=new_id)
    company_symbol: str | None = None
    subject_key: str
    effective_date: str  # ISO date or fiscal period key
    period_kind: PeriodKind = PeriodKind.POINT_IN_TIME
    version: int = 1
    previous_object_id: str | None = None
    knowledge: dict[str, Any] = Field(default_factory=dict)
    entity_refs: EntityRefs
    provenance: HistoricalProvenance
    created_at: datetime = Field(default_factory=utc_now)


class IngestionRun(BaseModel):
    run_id: str = Field(default_factory=new_id)
    mode: str = "bootstrap"  # bootstrap | incremental | correction
    collector_id: str
    symbols: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    status: str = "running"
    raw_accepted: int = 0
    raw_rejected: int = 0
    objects_written: int = 0
    detail: dict[str, Any] = Field(default_factory=dict)


class CoverageStatus(str, Enum):
    COMPLETE = "Complete"
    PARTIAL = "Partial"
    SPARSE = "Sparse"
    MISSING = "Missing"


class TimelineLink(BaseModel):
    """Causal / narrative link between timeline events or entities."""

    from_key: str
    to_key: str
    relation: str  # e.g. caused | affected | transmitted_to
    note: str | None = None


class TimelineEvent(BaseModel):
    """Chronological narrative node — Sprint 8.2 Timeline Intelligence."""

    event_id: str = Field(default_factory=new_id)
    scope: TimelineScope
    subject_key: str  # INFY | information_technology | nifty | india
    year: int
    date: str | None = None  # ISO when known
    title: str
    description: str | None = None
    importance: TimelineImportance = TimelineImportance.HIGH
    event_type: str = "institutional"
    source: Source = Source.DERIVED
    links: list[TimelineLink] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)


# ----- Sprint 8.3 Historical Relationship Intelligence -----


class RelationshipDomain(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MACRO = "macro"
    MARKET = "market"


class RelationshipType(str, Enum):
    # Company
    COMPETITOR = "Competitor"
    SUPPLIER = "Supplier"
    CUSTOMER = "Customer"
    PARENT = "Parent"
    SUBSIDIARY = "Subsidiary"
    JOINT_VENTURE = "Joint Venture"
    ACQUISITION_TARGET = "Acquisition Target"
    GLOBAL_PEER = "Global Peer"
    REVENUE_SENSITIVITY = "Revenue Sensitivity"
    DEMAND_DRIVER = "Demand Driver"
    # Sector
    SECTOR_LEADER = "Sector Leader"
    SECTOR_PEER = "Sector Peer"
    SECTOR_BENEFICIARY = "Sector Beneficiary"
    SECTOR_UNDER_PRESSURE = "Sector Under Pressure"
    # Macro / market causal
    POSITIVE_HISTORICAL_IMPACT = "Positive Historical Impact"
    NEGATIVE_HISTORICAL_IMPACT = "Negative Historical Impact"
    TRANSMISSION = "Transmission"
    CAUSED = "Caused"
    AFFECTED = "Affected"
    BENEFICIARY = "Beneficiary"
    UNDER_PRESSURE = "Under Pressure"


class RelationshipConfidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RelationshipDirection(str, Enum):
    DIRECTED = "directed"
    BIDIRECTIONAL = "bidirectional"


class RelationshipEvidence(BaseModel):
    """Traceable supporting evidence — required before publication."""

    evidence_id: str = Field(default_factory=new_id)
    kind: str  # historical_cycle | timeline_link | financial_period | institutional_catalog
    summary: str
    period: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    weight: float = 1.0


class HistoricalRelationship(BaseModel):
    """Evidence-backed historical cause-and-effect / structural link."""

    relationship_id: str = Field(default_factory=new_id)
    domain: RelationshipDomain
    source_key: str
    source_label: str
    target_key: str
    target_label: str
    relationship_type: RelationshipType
    direction: RelationshipDirection = RelationshipDirection.DIRECTED
    confidence: RelationshipConfidence = RelationshipConfidence.MEDIUM
    occurrences: int = 1
    average_delay: str | None = None  # e.g. "3 Trading Days"
    first_observed: str | None = None
    last_confirmed: str | None = None
    evidence: list[RelationshipEvidence] = Field(default_factory=list)
    chain: list[str] = Field(default_factory=list)  # intermediate transmission nodes
    version: int = 1
    published: bool = False
    status: str = "draft"  # draft | published | stale
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ----- Sprint 8.4 Historical Analogue Intelligence -----


class AnalogueScope(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MARKET = "market"
    MACRO = "macro"


class AnalogueConfidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class AnalogueDimensionScore(BaseModel):
    dimension: str
    current_value: float | str | None = None
    historical_value: float | str | None = None
    score: float  # 0-100
    matched: bool = True


class HistoricalAnalogue(BaseModel):
    """Ranked historically similar situation with explainable similarity."""

    analogue_id: str = Field(default_factory=new_id)
    scope: AnalogueScope
    current_entity: str
    matched_period: str
    matched_label: str | None = None
    similarity_score: float  # 0-100
    confidence: AnalogueConfidence = AnalogueConfidence.MEDIUM
    matching_dimensions: list[str] = Field(default_factory=list)
    non_matching_dimensions: list[str] = Field(default_factory=list)
    dimension_scores: list[AnalogueDimensionScore] = Field(default_factory=list)
    historical_outcome: str | None = None
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    timeline_refs: list[str] = Field(default_factory=list)
    relationship_refs: list[str] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)


class AnalogueQuery(BaseModel):
    """Structured analogue search request produced by Analogue Query Builder."""

    scope: AnalogueScope
    entity_key: str
    question: str | None = None
    as_of_period: str | None = None
    situation: str | None = None  # e.g. slowdown | margin_compression | rate_cut
    features: dict[str, float] = Field(default_factory=dict)
    top_k: int = 5
