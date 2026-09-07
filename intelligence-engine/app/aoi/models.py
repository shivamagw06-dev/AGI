"""AOI v1.0 domain models — registry, artifacts, facts, quality, ops."""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


DocumentFormat = Literal["pdf", "html", "xml", "json", "csv", "xlsx", "txt", "zip", "unknown"]
ArtifactStatus = Literal["discovered", "downloaded", "parsed", "extracted", "validated", "published", "failed", "skipped"]
FactField = str


class CompanyRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    company_name: str
    nse_symbol: str = ""
    bse_code: str = ""
    isin: str = ""
    cin: str = ""
    sector: str = ""
    industry: str = ""
    sub_industry: str = ""
    headquarters: str = ""
    website: str = ""
    investor_relations_url: str = ""
    exchange_urls: list[str] = Field(default_factory=list)
    annual_report_urls: list[str] = Field(default_factory=list)
    quarterly_result_urls: list[str] = Field(default_factory=list)
    presentation_urls: list[str] = Field(default_factory=list)
    earnings_call_urls: list[str] = Field(default_factory=list)
    sustainability_report_urls: list[str] = Field(default_factory=list)
    credit_rating_urls: list[str] = Field(default_factory=list)
    agm_urls: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    universe: str = "nifty_50"  # nifty_50 | nifty_next_50 | nifty_200 | nifty_500 | global
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_id: str
    source_name: str
    url: str = ""
    retrieved_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class DocumentArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(default_factory=lambda: _id("aoi_doc"))
    connector_id: str
    company_id: str | None = None
    title: str
    url: str = ""
    doc_type: str = "public_filing"  # annual_report, quarterly, presentation, macro, circular, ...
    format: DocumentFormat = "unknown"
    checksum: str = ""
    size_bytes: int = 0
    status: ArtifactStatus = "discovered"
    content_text: str = ""
    tables: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    discovered_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
    downloaded_at: str | None = None
    parsed_at: str | None = None
    published_at: str | None = None
    version: int = 1


class ExtractedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(default_factory=lambda: _id("aoi_fact"))
    company_id: str | None = None
    field: FactField
    value: Any = None
    value_text: str = ""
    source: SourceRef
    document_id: str = ""
    page: str | None = None
    section: str | None = None
    confidence: float = 0.5
    extracted_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
    version: int = 1
    previous_fact_id: str | None = None


class KnowledgeVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(default_factory=lambda: _id("aoi_ver"))
    company_id: str
    label: str  # e.g. Q1 FY26, Annual FY26
    period: str = ""
    fact_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
    change_summary: list[str] = Field(default_factory=list)


class StructuredDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diff_id: str = Field(default_factory=lambda: _id("aoi_diff"))
    company_id: str
    field: str
    old_value: str = ""
    new_value: str = ""
    change_type: str = "updated"  # new | updated | removed
    detected_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
    source_document_id: str = ""


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(default_factory=lambda: _id("aoi_edge"))
    src: str
    rel: str
    dst: str
    confidence: float = 0.7
    source_document_id: str = ""


class CompanyQualityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    nse_symbol: str = ""
    coverage: float = 0.0
    freshness: float = 0.0
    completeness: float = 0.0
    confidence: float = 0.0
    validation: float = 0.0
    missing_documents: float = 0.0
    extraction_quality: float = 0.0
    overall: float = 0.0


class GapTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(default_factory=lambda: _id("aoi_gap"))
    company_id: str | None = None
    kind: str
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    title: str
    detail: str = ""
    suggested_action: str = ""
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class DailyLearningDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    digest_id: str = Field(default_factory=lambda: _id("aoi_digest"))
    as_of: str
    companies_updated: int = 0
    earnings_released: int = 0
    acquisitions: int = 0
    guidance_revisions: int = 0
    promoter_changes: int = 0
    board_appointments: int = 0
    macro_releases: int = 0
    documents_ingested: int = 0
    facts_extracted: int = 0
    highlights: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class ConnectorHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_id: str
    name: str
    enabled: bool = True
    status: str = "unknown"  # ok | degraded | error | disabled
    last_run_at: str | None = None
    last_success_at: str | None = None
    latency_ms: float | None = None
    discovered: int = 0
    downloaded: int = 0
    failed: int = 0
    retries: int = 0
    error: str = ""


class ScheduleJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    connector_id: str
    cadence: str  # cron-like label: hourly | daily | event | earnings_hourly
    priority: int = 100
    enabled: bool = True
    last_run_at: str | None = None
    next_run_hint: str = ""


class ObservabilitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_latency_ms: dict[str, float] = Field(default_factory=dict)
    download_success: int = 0
    download_failed: int = 0
    parser_success: int = 0
    parser_failed: int = 0
    extraction_success: int = 0
    validation_success: int = 0
    knowledge_updates: int = 0
    queue_length: int = 0
    scheduler_health: str = "ok"
    errors: int = 0
    retries: int = 0
    knowledge_growth_facts: int = 0
    knowledge_growth_documents: int = 0


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: _id("aoi_audit"))
    action: str
    actor: str = "aoi"
    object_kind: str = ""
    object_id: str = ""
    detail: str = ""
    at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())
