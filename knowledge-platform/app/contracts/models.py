"""Stable KAIP/IKO contracts — Raw Events, Institutional Knowledge Objects, Learning Events."""

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


class KnowledgeObjectType(str, Enum):
    """Universal institutional knowledge types — Sprint 6.2 (exactly ten)."""

    COMPANY_PROFILE = "CompanyProfile"
    MARKET_SNAPSHOT = "MarketSnapshot"
    FINANCIAL_STATEMENT = "FinancialStatement"
    CORPORATE_EVENT = "CorporateEvent"
    CORPORATE_ACTION = "CorporateAction"
    OWNERSHIP = "Ownership"
    ANALYST_CONSENSUS = "AnalystConsensus"
    NEWS_EVENT = "NewsEvent"
    SECTOR_KNOWLEDGE = "SectorKnowledge"
    MARKET_KNOWLEDGE = "MarketKnowledge"


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class LearningCategory(str, Enum):
    FINANCIAL = "Financial"
    VALUATION = "Valuation"
    BUSINESS = "Business"
    OWNERSHIP = "Ownership"
    CORPORATE = "Corporate"
    MARKET = "Market"
    SECTOR = "Sector"
    NEWS = "News"


class Importance(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ValidationStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class RawEvent(BaseModel):
    event_id: str = Field(default_factory=new_id)
    source: Source
    collector_id: str
    endpoint: str
    company_symbol: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    checksum: str
    validation_status: ValidationStatus | None = None
    validation_errors: list[str] = Field(default_factory=list)


class EntityRefs(BaseModel):
    company_id: str | None = None
    company_name: str | None = None
    company_symbol: str | None = None
    sector: str | None = None
    industry: str | None = None
    indexes: list[str] = Field(default_factory=list)
    peers: list[str] = Field(default_factory=list)
    clients: list[str] = Field(default_factory=list)
    # Sector / market subjects
    sector_key: str | None = None
    market_key: str | None = None


class KnowledgeMetadata(BaseModel):
    """Required metadata on every Institutional Knowledge Object."""

    source: Source
    confidence: Confidence = Confidence.MEDIUM
    # Sprint 6.5 KCE — numeric trust for IE evidence weighting
    confidence_pct: float | None = None
    confidence_detail: dict[str, Any] | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    version: int = 1
    verified: bool = True
    collector_id: str | None = None


class KnowledgeObject(BaseModel):
    object_type: KnowledgeObjectType
    object_id: str = Field(default_factory=new_id)
    # Subject: company symbol OR sector_key OR market_key
    company_symbol: str | None = None
    sector_key: str | None = None
    market_key: str | None = None
    subject_key: str
    version: int = 1
    previous_object_id: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    change_summary: str | None = None
    knowledge: dict[str, Any] = Field(default_factory=dict)
    # Backward-compatible alias used by Sprint 6.1 paths
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: KnowledgeMetadata
    entity_refs: EntityRefs
    published_at: datetime | None = None
    source_event_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class LearningEvent(BaseModel):
    learning_id: str = Field(default_factory=new_id)
    company_symbol: str | None = None
    sector_key: str | None = None
    market_key: str | None = None
    category: LearningCategory = LearningCategory.FINANCIAL
    category_label: str = "Financial Performance"
    importance: Importance = Importance.MEDIUM
    confidence: Confidence = Confidence.MEDIUM
    field_name: str
    previous_value: Any = None
    new_value: Any = None
    delta: Any = None
    materiality: str = "material"
    materiality_score: float = 0.0
    reason: str
    observation: str = ""
    evidence: str = ""
    affected: list[str] = Field(default_factory=list)
    object_type: KnowledgeObjectType | None = None
    object_id: str | None = None
    source_event_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    published_at: datetime | None = None


class PublicationEnvelope(BaseModel):
    """Layered publication target for IE / Evidence Graph / Institutional Memory."""

    company_knowledge: list[KnowledgeObject] = Field(default_factory=list)
    sector_knowledge: list[KnowledgeObject] = Field(default_factory=list)
    market_knowledge: list[KnowledgeObject] = Field(default_factory=list)
    learning_events: list[LearningEvent] = Field(default_factory=list)
    sector_learning: list[dict[str, Any]] = Field(default_factory=list)
    market_learning: list[dict[str, Any]] = Field(default_factory=list)
    institutional_memory: list[dict[str, Any]] = Field(default_factory=list)
    learning_timeline: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    evidence_graph_ready: bool = True
    institutional_memory_ready: bool = True
    published_at: datetime = Field(default_factory=utc_now)


class PublishedBundle(BaseModel):
    knowledge_objects: list[KnowledgeObject] = Field(default_factory=list)
    learning_events: list[LearningEvent] = Field(default_factory=list)
    envelope: PublicationEnvelope | None = None
    ile: dict[str, Any] = Field(default_factory=dict)
