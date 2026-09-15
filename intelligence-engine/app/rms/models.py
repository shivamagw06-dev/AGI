"""RMS domain models — research lifecycle, reviews, publishing, compliance."""

from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


RMS_VERSION = "rms-v1.0.1"


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ResearchStatus(str, Enum):
    IDEA = "idea"
    RESEARCH_REQUEST = "research_request"
    KNOWLEDGE_COLLECTION = "knowledge_collection"
    RSP_REASONING = "rsp_reasoning"
    DRAFT = "draft"
    INTERNAL_REVIEW = "internal_review"
    COMPLIANCE_REVIEW = "compliance_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# Allowed forward transitions (plus revision/reject paths handled in workflow)
TRANSITIONS: dict[ResearchStatus, set[ResearchStatus]] = {
    ResearchStatus.IDEA: {ResearchStatus.RESEARCH_REQUEST, ResearchStatus.ARCHIVED},
    ResearchStatus.RESEARCH_REQUEST: {
        ResearchStatus.KNOWLEDGE_COLLECTION,
        ResearchStatus.RSP_REASONING,
        ResearchStatus.DRAFT,
        ResearchStatus.ARCHIVED,
        ResearchStatus.REJECTED,
    },
    ResearchStatus.KNOWLEDGE_COLLECTION: {
        ResearchStatus.RSP_REASONING,
        ResearchStatus.DRAFT,
        ResearchStatus.REJECTED,
    },
    ResearchStatus.RSP_REASONING: {
        ResearchStatus.DRAFT,
        ResearchStatus.REVISION_REQUESTED,
        ResearchStatus.REJECTED,
    },
    ResearchStatus.DRAFT: {
        ResearchStatus.INTERNAL_REVIEW,
        ResearchStatus.REVISION_REQUESTED,
        ResearchStatus.ARCHIVED,
    },
    ResearchStatus.INTERNAL_REVIEW: {
        ResearchStatus.COMPLIANCE_REVIEW,
        ResearchStatus.REVISION_REQUESTED,
        ResearchStatus.REJECTED,
        ResearchStatus.DRAFT,
    },
    ResearchStatus.COMPLIANCE_REVIEW: {
        ResearchStatus.APPROVED,
        ResearchStatus.REVISION_REQUESTED,
        ResearchStatus.REJECTED,
        ResearchStatus.DRAFT,
    },
    ResearchStatus.APPROVED: {
        ResearchStatus.PUBLISHED,
        ResearchStatus.REVISION_REQUESTED,
        ResearchStatus.ARCHIVED,
    },
    ResearchStatus.REJECTED: {ResearchStatus.ARCHIVED, ResearchStatus.DRAFT},
    ResearchStatus.REVISION_REQUESTED: {
        ResearchStatus.DRAFT,
        ResearchStatus.KNOWLEDGE_COLLECTION,
        ResearchStatus.RSP_REASONING,
        ResearchStatus.ARCHIVED,
    },
    ResearchStatus.PUBLISHED: {ResearchStatus.ARCHIVED},
    ResearchStatus.ARCHIVED: set(),
}


class ReviewDecision(str, Enum):
    COMMENT = "comment"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"


class ReviewType(str, Enum):
    INTERNAL = "internal"
    COMPLIANCE = "compliance"
    GENERAL = "general"


class ReviewComment(BaseModel):
    comment_id: str = Field(default_factory=lambda: _new_id("cmt"))
    author: str
    body: str
    decision: ReviewDecision = ReviewDecision.COMMENT
    review_type: ReviewType = ReviewType.GENERAL
    created_at: _dt.datetime = Field(default_factory=_utcnow)


class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: _new_id("apr"))
    approver: str
    role: str = "reviewer"
    decision: Literal["approved", "rejected", "revision_requested"] = "approved"
    notes: str = ""
    created_at: _dt.datetime = Field(default_factory=_utcnow)


class PublicationArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: _new_id("pub"))
    channel: Literal["website", "newsletter", "linkedin", "internal_archive"]
    title: str
    body: str = ""
    url: str = ""
    status: str = "created"
    created_at: _dt.datetime = Field(default_factory=_utcnow)


class PublishingHistoryEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: _new_id("ph"))
    action: str
    actor: str = "system"
    timestamp: _dt.datetime = Field(default_factory=_utcnow)
    details: dict[str, Any] = Field(default_factory=dict)


class ComplianceRecord(BaseModel):
    review_history: list[ReviewComment] = Field(default_factory=list)
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    reasoning_version: str = ""
    evidence_version: str = ""
    engine_versions: dict[str, str] = Field(default_factory=dict)
    document_versions: list[str] = Field(default_factory=list)
    publication_timestamp: _dt.datetime | None = None


class ResearchObject(BaseModel):
    research_id: str = Field(default_factory=lambda: _new_id("rms"))
    title: str
    status: ResearchStatus = ResearchStatus.IDEA
    owner: str = ""
    reviewer: str = ""
    version: int = 1
    tickers: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    idea_summary: str = ""
    request_brief: str = ""
    draft_body: str = ""
    evidence_package: dict[str, Any] = Field(default_factory=dict)
    reasoning_package: dict[str, Any] = Field(default_factory=dict)
    reasoning_id: str | None = None
    engine_snapshot: dict[str, Any] = Field(default_factory=dict)
    house_view: dict[str, Any] | None = None
    prediction_horizon: str = "90d"
    prediction_ids: list[str] = Field(default_factory=list)
    kip_document_ids: list[str] = Field(default_factory=list)
    publishing_history: list[PublishingHistoryEntry] = Field(default_factory=list)
    publication_artifacts: list[PublicationArtifact] = Field(default_factory=list)
    compliance: ComplianceRecord = Field(default_factory=ComplianceRecord)
    assignments: dict[str, str] = Field(default_factory=dict)  # role -> person
    metadata: dict[str, Any] = Field(default_factory=dict)
    rms_version: str = RMS_VERSION
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    updated_at: _dt.datetime = Field(default_factory=_utcnow)
    published_at: _dt.datetime | None = None


class ResearchRequestCreate(BaseModel):
    title: str
    owner: str = "analyst"
    reviewer: str = ""
    tickers: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    idea_summary: str = ""
    request_brief: str = ""
    prediction_horizon: str = "90d"
    collect_knowledge: bool = True
    run_rsp: bool = True
    engine_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftRequest(BaseModel):
    research_id: str | None = None
    title: str = ""
    owner: str = "analyst"
    tickers: list[str] = Field(default_factory=list)
    draft_body: str = ""
    run_rsp: bool = True
    engine_snapshot: dict[str, Any] = Field(default_factory=dict)
    submit_for_review: bool = False


class ReviewRequest(BaseModel):
    research_id: str
    author: str
    body: str = ""
    decision: ReviewDecision = ReviewDecision.COMMENT
    review_type: ReviewType = ReviewType.INTERNAL


class ApproveRequest(BaseModel):
    research_id: str
    approver: str
    notes: str = ""
    role: str = "approver"


class PublishRequest(BaseModel):
    research_id: str
    actor: str = "publisher"
    channels: list[Literal["website", "newsletter", "linkedin", "internal_archive"]] = Field(
        default_factory=lambda: ["website", "newsletter", "linkedin", "internal_archive"]
    )
    ingest_kip: bool = True
    track_predictions: bool = True


class PipelineCounts(BaseModel):
    idea: int = 0
    research_request: int = 0
    knowledge_collection: int = 0
    rsp_reasoning: int = 0
    draft: int = 0
    internal_review: int = 0
    compliance_review: int = 0
    approved: int = 0
    rejected: int = 0
    revision_requested: int = 0
    published: int = 0
    archived: int = 0


class RmsDashboard(BaseModel):
    research_pipeline: PipelineCounts = Field(default_factory=PipelineCounts)
    draft_queue: list[str] = Field(default_factory=list)
    review_queue: list[str] = Field(default_factory=list)
    publication_calendar: list[dict[str, Any]] = Field(default_factory=list)
    prediction_tracker: list[dict[str, Any]] = Field(default_factory=list)
    research_coverage: dict[str, int] = Field(default_factory=dict)
    company_coverage: dict[str, int] = Field(default_factory=dict)
    sector_coverage: dict[str, int] = Field(default_factory=dict)
    totals: dict[str, int] = Field(default_factory=dict)
    rms_version: str = RMS_VERSION
