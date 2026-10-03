"""RSP domain models — ReasoningPackage and institutional evidence."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


REASONING_VERSION = "rsp-v1.0.1"


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class EvidenceStatement(BaseModel):
    evidence_id: str = Field(default_factory=lambda: _new_id("ev"))
    statement: str
    kind: Literal["fact", "opinion"] = "opinion"
    source: str = ""
    reliability: float = 0.5
    freshness: float = 0.5
    confidence: float = 0.5
    score: float = 0.5
    supporting_documents: list[str] = Field(default_factory=list)
    contradicting_documents: list[str] = Field(default_factory=list)
    engine_support: list[str] = Field(default_factory=list)
    house_view_alignment: Literal["aligned", "contrary", "neutral", "unknown"] = "unknown"
    cluster: str = ""  # bull / bear / base / valuation / risk / catalyst / macro


class Contradiction(BaseModel):
    contradiction_id: str = Field(default_factory=lambda: _new_id("ctr"))
    kind: str
    summary: str
    left_source: str = ""
    right_source: str = ""
    left_claim: str = ""
    right_claim: str = ""
    severity: float = 0.5
    document_ids: list[str] = Field(default_factory=list)


class OpinionCluster(BaseModel):
    cluster_id: str
    label: str
    stance: str = "neutral"
    statements: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    weight: float = 0.0


class ConsensusView(BaseModel):
    agi_view: str = ""
    broker_consensus: str = ""
    market_consensus: str = ""
    contrarian_view: str = ""
    unknown_areas: list[str] = Field(default_factory=list)
    agreement_score: float = 0.0


class ChangeDetection(BaseModel):
    what_changed: list[str] = Field(default_factory=list)
    what_stayed_the_same: list[str] = Field(default_factory=list)
    invalidated_previous_research: list[str] = Field(default_factory=list)
    strengthens_thesis: list[str] = Field(default_factory=list)
    weakens_thesis: list[str] = Field(default_factory=list)


class ResearchSynthesis(BaseModel):
    research_brief: str = ""
    investment_thesis: str = ""
    counter_thesis: str = ""
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    valuation_summary: str = ""
    confidence: float = 0.0
    evidence_tree: dict[str, Any] = Field(default_factory=dict)


class EvidenceTreeNode(BaseModel):
    node_id: str
    label: str
    children: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ReasoningValidation(BaseModel):
    evidence_tree: dict[str, Any] = Field(default_factory=dict)
    supporting_documents: list[str] = Field(default_factory=list)
    contradicting_documents: list[str] = Field(default_factory=list)
    house_view_alignment: str = "unknown"
    freshness: float = 0.0
    confidence: float = 0.0
    reasoning_version: str = REASONING_VERSION


class ReasoningPackage(BaseModel):
    reasoning_id: str = Field(default_factory=lambda: _new_id("rsp"))
    question: str
    ticker: str | None = None
    facts: list[EvidenceStatement] = Field(default_factory=list)
    opinions: list[EvidenceStatement] = Field(default_factory=list)
    evidence: list[EvidenceStatement] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    opinion_clusters: list[OpinionCluster] = Field(default_factory=list)
    consensus: ConsensusView = Field(default_factory=ConsensusView)
    confidence: float = 0.0
    house_view: dict[str, Any] | None = None
    research_continuity: ChangeDetection = Field(default_factory=ChangeDetection)
    synthesis: ResearchSynthesis = Field(default_factory=ResearchSynthesis)
    ranked_sources: list[dict[str, Any]] = Field(default_factory=list)
    pipeline_stages: list[str] = Field(default_factory=list)
    engine_inputs: dict[str, Any] = Field(default_factory=dict)
    validation: ReasoningValidation = Field(default_factory=ReasoningValidation)
    reasoning_version: str = REASONING_VERSION
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    answer_policy: str = "rsp_reasons_before_llm"


class EngineBundle(BaseModel):
    """Optional engine/L4/portfolio inputs — consumed as evidence, never redesigned."""

    e01: dict[str, Any] | None = None
    e02: dict[str, Any] | None = None
    e03: dict[str, Any] | None = None
    e04: dict[str, Any] | None = None
    e05: dict[str, Any] | None = None
    e08: dict[str, Any] | None = None
    e09: dict[str, Any] | None = None
    e11: dict[str, Any] | None = None
    e13: dict[str, Any] | None = None
    e14: dict[str, Any] | None = None
    l4: dict[str, Any] | None = None
    e10: dict[str, Any] | None = None


class ReasonRequest(BaseModel):
    question: str
    ticker: str | None = None
    # Optional pre-fetched KIP context; if absent RSP will call KipService when wired
    kip_context: dict[str, Any] | None = None
    house_view: dict[str, Any] | None = None
    engines: EngineBundle = Field(default_factory=EngineBundle)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SynthesizeRequest(BaseModel):
    reasoning_id: str | None = None
    question: str = ""
    ticker: str | None = None
    kip_context: dict[str, Any] | None = None
    house_view: dict[str, Any] | None = None
    engines: EngineBundle = Field(default_factory=EngineBundle)


class CommitteeRequest(BaseModel):
    """Full Research Committee pass — reason + synthesize in one call."""

    question: str
    ticker: str | None = None
    kip_context: dict[str, Any] | None = None
    house_view: dict[str, Any] | None = None
    engines: EngineBundle = Field(default_factory=EngineBundle)
    metadata: dict[str, Any] = Field(default_factory=dict)
