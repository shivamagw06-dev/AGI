"""EVE domain models — evidence, provenance, trust, conflicts, timeline."""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


VerificationStatus = Literal[
    "unverified",
    "pending",
    "verified",
    "conflicted",
    "stale",
    "rejected",
    "soft_deleted",
]


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    name: str
    category: str
    organisation: str = ""
    country: str = ""
    website: str = ""
    authority_level: str = "standard"
    reliability_score: float = 0.5
    update_frequency: str = "unknown"
    license_notes: str = ""
    last_successful_sync: str | None = None
    parser_version: str = "eve-1.0"
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_name: str = ""
    document_id: str = ""
    url: str = ""
    file_checksum: str = ""
    page: str | None = None
    section: str | None = None
    extraction_timestamp: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
    observation_timestamp: str | None = None
    connector: str = ""
    parser: str = "eve-parser-1.0"
    model_version: str = "eve-v1.0.0"
    verification_status: VerificationStatus = "unverified"
    evidence_id: str = ""
    knowledge_id: str | None = None


class EvidenceObject(BaseModel):
    """Immutable evidence record for one observed fact assertion."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(default_factory=lambda: _id("eve_ev"))
    fact_key: str  # canonical fact field
    raw_field: str = ""
    value: Any = None
    value_text: str = ""
    company_id: str | None = None
    company_symbol: str = ""
    unit: str = ""
    period: str = ""
    provenance: Provenance
    confidence: float = 0.5
    verification_status: VerificationStatus = "unverified"
    supporting_source_ids: list[str] = Field(default_factory=list)
    parser_confidence: float = 0.7
    extraction_quality: float = 0.7
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
    last_confirmed_at: str | None = None
    soft_deleted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(default_factory=lambda: _id("eve_fv"))
    fact_key: str
    company_id: str | None = None
    previous_value: str = ""
    new_value: str = ""
    reason: str = ""
    effective_date: str | None = None
    source_id: str = ""
    evidence_id: str = ""
    confidence: float = 0.5
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class ConflictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(default_factory=lambda: _id("eve_cf"))
    company_id: str | None = None
    fact_key: str
    left_evidence_id: str
    right_evidence_id: str
    left_value: str = ""
    right_value: str = ""
    left_source_id: str = ""
    right_source_id: str = ""
    status: str = "open"  # open | acknowledged | resolved
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    verification_task: str = ""
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
    resolved_at: str | None = None


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: _id("eve_tl"))
    company_id: str | None = None
    company_symbol: str = ""
    event_type: str
    title: str
    detail: str = ""
    event_date: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.6
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class RelationshipEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationship_id: str = Field(default_factory=lambda: _id("eve_rel"))
    src: str
    rel: str
    dst: str
    confidence: float = 0.6
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = "unverified"


class CompanyKnowledgeHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    company_symbol: str = ""
    evidence_count: int = 0
    verification_pct: float = 0.0
    unverified_facts: int = 0
    conflicts: int = 0
    average_confidence: float = 0.0
    freshness: float = 0.0
    coverage: float = 0.0
    trust_score: float = 0.0


class VerificationTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default_factory=lambda: _id("eve_vt"))
    kind: str
    company_id: str | None = None
    fact_key: str = ""
    title: str
    detail: str = ""
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    status: str = "open"
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(default_factory=lambda: _id("eve_au"))
    action: str
    actor: str = "eve"
    object_kind: str = ""
    object_id: str = ""
    detail: str = ""
    at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class EveMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_count: int = 0
    verified_facts: int = 0
    conflicts: int = 0
    average_confidence: float = 0.0
    verification_latency_ms: float = 0.0
    source_reliability_avg: float = 0.0
    failed_validations: int = 0
    parser_accuracy: float = 0.0
    evidence_growth: int = 0
    knowledge_health_avg: float = 0.0
