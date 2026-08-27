"""AWS workspace response models — aggregation only, no new research logic."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Literal

from pydantic import BaseModel, Field


AWS_VERSION = "aws-v1.0.1"


class WorkspaceMeta(BaseModel):
    workspace: str
    aws_version: str = AWS_VERSION
    generated_at: _dt.datetime = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
    sources: list[str] = Field(default_factory=list)


class CompanyWorkspace(BaseModel):
    meta: WorkspaceMeta
    ticker: str
    house_view: dict[str, Any] | None = None
    l4_opinion: dict[str, Any] | None = None
    macro: dict[str, Any] | None = None
    factors: dict[str, Any] | None = None
    technical: dict[str, Any] | None = None  # E03 alpha / cross-section
    fundamental: dict[str, Any] | None = None
    volatility: dict[str, Any] | None = None
    trend: dict[str, Any] | None = None
    relative_value: dict[str, Any] | None = None
    events: dict[str, Any] | None = None
    sentiment: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None
    portfolio_weight: float | None = None
    portfolio: dict[str, Any] | None = None
    replay_statistics: dict[str, Any] | None = None
    prediction_history: list[dict[str, Any]] = Field(default_factory=list)
    research_timeline: dict[str, Any] | None = None
    latest_news: list[dict[str, Any]] = Field(default_factory=list)
    broker_research: list[dict[str, Any]] = Field(default_factory=list)
    agi_articles: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_graph: dict[str, Any] | None = None
    dossier: dict[str, Any] | None = None


class ThemeWorkspace(BaseModel):
    meta: WorkspaceMeta
    theme_id: str
    theme: dict[str, Any] | None = None
    related_companies: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    knowledge_graph: dict[str, Any] | None = None
    search_hits: list[dict[str, Any]] = Field(default_factory=list)


class SectorWorkspace(BaseModel):
    meta: WorkspaceMeta
    sector_id: str
    company_coverage: dict[str, int] = Field(default_factory=dict)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    portfolio_exposure: dict[str, Any] | None = None
    rms_research: list[dict[str, Any]] = Field(default_factory=list)


class MacroWorkspace(BaseModel):
    meta: WorkspaceMeta
    e01: dict[str, Any] | None = None
    e14: dict[str, Any] | None = None
    macro_documents: list[dict[str, Any]] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


class PortfolioWorkspace(BaseModel):
    meta: WorkspaceMeta
    current_portfolio: dict[str, Any] | None = None
    historical_portfolio: list[dict[str, Any]] = Field(default_factory=list)
    risk: dict[str, Any] | None = None
    sector_exposure: dict[str, Any] = Field(default_factory=dict)
    country_exposure: dict[str, Any] = Field(default_factory=dict)
    performance: dict[str, Any] | None = None
    attribution: dict[str, Any] | None = None
    l4_book: dict[str, Any] | None = None


class ResearchWorkspace(BaseModel):
    meta: WorkspaceMeta
    research_id: str | None = None
    current_draft: dict[str, Any] | None = None
    evidence_package: dict[str, Any] | None = None
    reasoning_package: dict[str, Any] | None = None
    research_timeline: dict[str, Any] | None = None
    supporting_documents: list[str] = Field(default_factory=list)
    conflicting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    review_status: str | None = None
    approval_status: str | None = None
    publishing_status: str | None = None
    draft_queue: list[str] = Field(default_factory=list)
    review_queue: list[str] = Field(default_factory=list)


class ReplayWorkspace(BaseModel):
    meta: WorkspaceMeta
    as_of: str
    engine_outputs: dict[str, Any] = Field(default_factory=dict)
    l4: dict[str, Any] | None = None
    portfolio: dict[str, Any] | None = None
    research: list[dict[str, Any]] = Field(default_factory=list)
    predictions: list[dict[str, Any]] = Field(default_factory=list)
    performance: dict[str, Any] | None = None
    replay_run: dict[str, Any] | None = None


class CreWorkspace(BaseModel):
    meta: WorkspaceMeta
    dashboard: dict[str, Any] | None = None
    scorecards: list[dict[str, Any]] = Field(default_factory=list)
    composite: dict[str, Any] | None = None
    alerts: dict[str, Any] | None = None
    promotion: dict[str, Any] | None = None


class AwsDashboard(BaseModel):
    meta: WorkspaceMeta
    workspaces: list[str] = Field(
        default_factory=lambda: [
            "company",
            "sector",
            "theme",
            "macro",
            "portfolio",
            "research",
            "replay",
            "cre",
        ]
    )
    platform_health: dict[str, Any] = Field(default_factory=dict)
    portfolio: dict[str, Any] | None = None
    cre: dict[str, Any] | None = None
    rms: dict[str, Any] | None = None
    kip_stats: dict[str, Any] | None = None
    rsp_stats: dict[str, Any] | None = None
    recent_research: list[dict[str, Any]] = Field(default_factory=list)


class SearchHit(BaseModel):
    kind: str  # company | theme | report | sector | broker | research | prediction | people
    id: str
    title: str
    score: float = 0.0
    ticker: str | None = None
    snippet: str = ""
    source: str = ""


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit] = Field(default_factory=list)
    aws_version: str = AWS_VERSION


class CopilotContext(BaseModel):
    """Context-aware copilot pack — never starts from an empty prompt."""

    workspace: str
    ticker: str | None = None
    theme_id: str | None = None
    sector_id: str | None = None
    research_id: str | None = None
    as_of: str | None = None
    question: str = ""
    kip: dict[str, Any] | None = None
    rsp: dict[str, Any] | None = None
    l4: dict[str, Any] | None = None
    portfolio: dict[str, Any] | None = None
    research: dict[str, Any] | None = None
    house_view: dict[str, Any] | None = None
    engines: dict[str, Any] = Field(default_factory=dict)
    answer_policy: str = "context_aware_never_empty"
    aws_version: str = AWS_VERSION


class KnowledgeExplorer(BaseModel):
    meta: WorkspaceMeta
    entity: str
    graph: dict[str, Any] | None = None
    company_links: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    macro_drivers: list[str] = Field(default_factory=list)
    research_relationships: list[dict[str, Any]] = Field(default_factory=list)
