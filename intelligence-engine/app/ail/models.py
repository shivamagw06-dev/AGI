"""AIL domain models — evidence-backed, versioned, immutable where required."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class EvidenceRecord(BaseModel):
    evidence_id: str = Field(default_factory=lambda: new_id("EV"))
    claim: str
    company: str | None = None
    ticker: str | None = None
    source: str
    url: str | None = None
    page: int | None = None
    section: str | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)
    connector: str = "ail"
    authority_score: int = 5
    confidence: float = 0.7
    content_hash: str = ""
    document_version: str | None = None
    validation_status: str = "registered"
    verified_against: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash:
            self.content_hash = sha256_text(
                f"{self.claim}|{self.source}|{self.url}|{self.page}|{self.section}"
            )

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["retrieved_at"] = self.retrieved_at.isoformat()
        return d


class ProvenancedField(BaseModel):
    value: Any = None
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class DossierVersion(BaseModel):
    dossier_id: str = Field(default_factory=lambda: new_id("DOS"))
    ticker: str
    company: str
    version: int = 1
    fields: dict[str, ProvenancedField] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    supersedes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "ticker": self.ticker,
            "company": self.company,
            "version": self.version,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "created_at": self.created_at.isoformat(),
            "supersedes": self.supersedes,
        }


class CorporateEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("EVT"))
    company: str
    ticker: str
    timestamp: datetime = Field(default_factory=utc_now)
    category: str
    importance: int = 5  # 1-10
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.6
    previous_value: str | None = None
    new_value: str | None = None
    impact: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["timestamp"] = self.timestamp.isoformat()
        return d


class ThesisCase(BaseModel):
    case: str  # bull | base | bear
    drivers: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    probability: float = 0.33
    confidence: float = 0.5
    invalidation_conditions: list[str] = Field(default_factory=list)
    expected_timeline: str = "12-24 months"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ThesisVersion(BaseModel):
    thesis_id: str = Field(default_factory=lambda: new_id("TH"))
    ticker: str
    company: str
    version: int = 1
    bull: ThesisCase
    base: ThesisCase
    bear: ThesisCase
    explanation: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    supersedes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "thesis_id": self.thesis_id,
            "ticker": self.ticker,
            "company": self.company,
            "version": self.version,
            "bull": self.bull.to_dict(),
            "base": self.base.to_dict(),
            "bear": self.bear.to_dict(),
            "explanation": self.explanation,
            "created_at": self.created_at.isoformat(),
            "supersedes": self.supersedes,
        }


class ForecastDistribution(BaseModel):
    metric: str
    unit: str = ""
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    mean: float | None = None
    samples: list[float] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class PredictionRecord(BaseModel):
    prediction_id: str = Field(default_factory=lambda: new_id("PR"))
    ticker: str
    company: str
    version: int = 1
    model_version: str = "ail-pe-v1.0"
    prediction_date: datetime = Field(default_factory=utc_now)
    review_date: str | None = None
    scenario: dict[str, dict[str, Any]] = Field(default_factory=dict)  # bull/base/bear
    distributions: list[ForecastDistribution] = Field(default_factory=list)
    sensitivity: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.55
    outcome: dict[str, Any] | None = None  # filled later; never overwrite prediction body

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "ticker": self.ticker,
            "company": self.company,
            "version": self.version,
            "model_version": self.model_version,
            "prediction_date": self.prediction_date.isoformat(),
            "review_date": self.review_date,
            "scenario": self.scenario,
            "distributions": [d.to_dict() for d in self.distributions],
            "sensitivity": self.sensitivity,
            "inputs": self.inputs,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
            "outcome": self.outcome,
        }


class TimelineEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: new_id("TL"))
    ticker: str
    company: str
    year: int | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    title: str
    category: str = "update"
    evidence_ids: list[str] = Field(default_factory=list)
    event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["timestamp"] = self.timestamp.isoformat()
        return d


class GraphEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: new_id("GE"))
    src: str
    rel: str
    dst: str
    evidence_ids: list[str] = Field(default_factory=list)
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class AuditRecord(BaseModel):
    audit_id: str = Field(default_factory=lambda: new_id("AUD"))
    query: str
    ticker: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    thesis_version: str | None = None
    prediction_version: str | None = None
    dossier_version: str | None = None
    reasoning_inputs: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["created_at"] = self.created_at.isoformat()
        return d
