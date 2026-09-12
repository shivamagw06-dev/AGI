"""FRE domain models — documents, chunks, evidence, graph, metrics."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def checksum_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


class QueryUnderstanding(BaseModel):
    query: str
    intent: str = "general_research"
    intents: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    time_periods: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    primary_entity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class RetrievalTask(BaseModel):
    task_id: str = Field(default_factory=lambda: new_id("task"))
    description: str
    document_types: list[str] = Field(default_factory=list)
    preferred_tiers: list[int] = Field(default_factory=lambda: [1, 2, 3, 4])
    company: str | None = None
    symbol: str | None = None
    priority: int = 5

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class QueryPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: new_id("qplan"))
    query: str
    understanding: QueryUnderstanding
    tasks: list[RetrievalTask] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "query": self.query,
            "understanding": self.understanding.to_dict(),
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at.isoformat(),
        }


class FreDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: new_id("doc"))
    title: str
    url: str = ""
    source: str = "unknown"
    document_type: str = "unknown"
    organisation: str = ""
    company: str | None = None
    symbol: str | None = None
    author: str | None = None
    published_at: str | None = None
    financial_year: str | None = None
    quarter: str | None = None
    region: str = "IN"
    language: str = "en"
    content_type: str = "text/plain"
    raw_text: str = ""
    checksum: str = ""
    authority: int = 2
    tier: int = 6
    retrieved_at: datetime = Field(default_factory=utc_now)
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    def ensure_checksum(self) -> None:
        if not self.checksum:
            self.checksum = checksum_text(self.raw_text or self.title)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["retrieved_at"] = self.retrieved_at.isoformat()
        return d


class FreChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: new_id("chk"))
    document_id: str
    text: str
    heading: str = ""
    section: str = ""
    page: int | None = None
    company: str | None = None
    symbol: str | None = None
    document_type: str = "unknown"
    source: str = "unknown"
    published_at: str | None = None
    reporting_period: str | None = None
    region: str = "IN"
    language: str = "en"
    authority: int = 2
    confidence: float = 0.7
    token_estimate: int = 0
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        # Keep embeddings out of default API dumps unless requested
        d.pop("embedding", None)
        return d


class FreEvidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: new_id("fev"))
    claim: str
    source: str
    document_id: str
    chunk_id: str
    page: int | None = None
    section: str = ""
    company: str | None = None
    symbol: str | None = None
    document_type: str = "unknown"
    published_at: str | None = None
    confidence: float = 0.5
    authority: int = 2
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    contradictory_evidence_ids: list[str] = Field(default_factory=list)
    validation_status: str = "unvalidated"
    created_at: datetime = Field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["created_at"] = self.created_at.isoformat()
        return d


class GraphNode(BaseModel):
    node_id: str = Field(default_factory=lambda: new_id("node"))
    label: str
    kind: str = "entity"
    company: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class GraphEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: new_id("edge"))
    source_id: str
    target_id: str
    relation: str
    confidence: float = 0.6
    evidence_ids: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class FreMetrics(BaseModel):
    documents_processed: int = 0
    documents_failed: int = 0
    chunks_indexed: int = 0
    evidence_extracted: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    parse_failures: int = 0
    last_ingest_at: str | None = None
    last_query_at: str | None = None
    avg_embed_ms: float = 0.0
    avg_search_ms: float = 0.0
    avg_retrieval_ms: float = 0.0

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        return super().model_dump(**kwargs)


_NUM_RE = re.compile(
    r"(?i)(revenue|sales|pat|profit|ebitda|margin|eps|guidance|growth|order\s*book)"
    r"[^.%]{0,80}?(\d+(?:\.\d+)?\s*%|\d+(?:,\d{3})*(?:\.\d+)?\s*(?:crore|cr|billion|mn|%)?)"
)


def extract_claim_candidates(text: str, limit: int = 3) -> list[str]:
    claims: list[str] = []
    for match in _NUM_RE.finditer(text or ""):
        span = text[max(0, match.start() - 40) : min(len(text), match.end() + 40)].strip()
        span = re.sub(r"\s+", " ", span)
        if span and span not in claims:
            claims.append(span[:220])
        if len(claims) >= limit:
            break
    if not claims and text:
        claims.append(re.sub(r"\s+", " ", text.strip())[:220])
    return claims
