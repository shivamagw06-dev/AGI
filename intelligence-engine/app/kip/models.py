"""KIP domain models — documents, chunks, graph, search, RAG evidence."""

from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class DocumentType(str, Enum):
    # Priority 1 — AGI house corpus
    AGI_RESEARCH = "agi_research"
    AGI_NOTE = "agi_note"
    AGI_CIO_REPORT = "agi_cio_report"
    AGI_DAILY_BRIEF = "agi_daily_brief"
    AGI_INVESTMENT_OFFICE = "agi_investment_office"
    AGI_MODEL_PORTFOLIO = "agi_model_portfolio"
    # Priority 2 — broker / sell-side / buy-side / newsletters
    BROKER_RESEARCH = "broker_research"
    BROKER_EMAIL = "broker_email"
    STRATEGY_NOTE = "strategy_note"
    SELL_SIDE = "sell_side"
    BUY_SIDE = "buy_side"
    NEWSLETTER = "newsletter"
    # Priority 3 — filings / transcripts / presentations
    SEC_FILING = "sec_filing"
    NSE_BSE_FILING = "nse_bse_filing"
    EARNINGS_TRANSCRIPT = "earnings_transcript"
    INVESTOR_PRESENTATION = "investor_presentation"
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    # Priority 4 — macro / news / government
    GOVERNMENT_REPORT = "government_report"
    CENTRAL_BANK_REPORT = "central_bank_report"
    INDUSTRY_REPORT = "industry_report"
    COMMODITY_REPORT = "commodity_report"
    MACRO_REPORT = "macro_report"
    MARKET_NEWS = "market_news"
    OTHER = "other"


# Retrieval priority: 1 = highest (AGI house view first)
SOURCE_PRIORITY: dict[str, int] = {
    DocumentType.AGI_RESEARCH.value: 1,
    DocumentType.AGI_NOTE.value: 1,
    DocumentType.AGI_CIO_REPORT.value: 1,
    DocumentType.AGI_DAILY_BRIEF.value: 1,
    DocumentType.AGI_INVESTMENT_OFFICE.value: 1,
    DocumentType.AGI_MODEL_PORTFOLIO.value: 1,
    DocumentType.BROKER_RESEARCH.value: 4,
    DocumentType.BROKER_EMAIL.value: 4,
    DocumentType.STRATEGY_NOTE.value: 4,
    DocumentType.SELL_SIDE.value: 4,
    DocumentType.BUY_SIDE.value: 4,
    DocumentType.NEWSLETTER.value: 4,
    DocumentType.MARKET_NEWS.value: 5,
    DocumentType.SEC_FILING.value: 6,
    DocumentType.NSE_BSE_FILING.value: 6,
    DocumentType.EARNINGS_TRANSCRIPT.value: 6,
    DocumentType.INVESTOR_PRESENTATION.value: 6,
    DocumentType.ANNUAL_REPORT.value: 6,
    DocumentType.QUARTERLY_REPORT.value: 6,
    DocumentType.GOVERNMENT_REPORT.value: 7,
    DocumentType.CENTRAL_BANK_REPORT.value: 7,
    DocumentType.INDUSTRY_REPORT.value: 7,
    DocumentType.COMMODITY_REPORT.value: 7,
    DocumentType.MACRO_REPORT.value: 7,
    DocumentType.OTHER.value: 7,
}


class DocumentMetadata(BaseModel):
    title: str = ""
    author: str = ""
    source: str = ""
    date: _dt.date | None = None
    document_type: DocumentType = DocumentType.OTHER
    broker: str = ""
    language: str = "en"
    version: int = 1


class InvestmentMetadata(BaseModel):
    companies: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    macro_topics: list[str] = Field(default_factory=list)


class ResearchMetadata(BaseModel):
    investment_thesis: str = ""
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    counter_arguments: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    valuation: str = ""
    forecasts: list[str] = Field(default_factory=list)
    target_prices: list[str] = Field(default_factory=list)
    expected_return: str = ""
    time_horizon: str = ""
    assumptions: list[str] = Field(default_factory=list)
    key_metrics: dict[str, str] = Field(default_factory=dict)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    charts: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    timeline_events: list[dict[str, Any]] = Field(default_factory=list)


class KnowledgeMetadata(BaseModel):
    freshness: float = 1.0
    confidence: float = 0.5
    source_reliability: float = 0.7
    related_documents: list[str] = Field(default_factory=list)
    related_companies: list[str] = Field(default_factory=list)
    related_themes: list[str] = Field(default_factory=list)
    related_research: list[str] = Field(default_factory=list)
    summary: str = ""


class KipChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: _new_id("chk"))
    document_id: str
    lineage_id: str
    version: int = 1
    ordinal: int = 0
    text: str
    tokens: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)


class KipDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: _new_id("doc"))
    lineage_id: str = Field(default_factory=lambda: _new_id("lin"))
    article_id: str | None = None  # external CMS / website article id
    research_type: str = ""
    content: str = ""
    cleaned_content: str = ""
    ocr_applied: bool = False
    document: DocumentMetadata = Field(default_factory=DocumentMetadata)
    investment: InvestmentMetadata = Field(default_factory=InvestmentMetadata)
    research: ResearchMetadata = Field(default_factory=ResearchMetadata)
    knowledge: KnowledgeMetadata = Field(default_factory=KnowledgeMetadata)
    supersedes: str | None = None
    superseded_by: str | None = None
    knowledge_version: str = "kip-v1.0.1-p1"
    pipeline_stages: list[str] = Field(default_factory=list)
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    immutable: Literal[True] = True


class GraphNode(BaseModel):
    node_id: str
    kind: str
    label: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: _new_id("edge"))
    source: str
    target: str
    relation: str
    document_id: str | None = None
    weight: float = 1.0


class KnowledgeGraphView(BaseModel):
    entity: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: _new_id("evt"))
    ticker: str
    event_date: _dt.date
    event_type: str
    title: str
    document_id: str | None = None
    source: str = ""
    summary: str = ""


class ResearchTimeline(BaseModel):
    ticker: str
    events: list[TimelineEvent] = Field(default_factory=list)


class SearchHit(BaseModel):
    document_id: str
    lineage_id: str
    version: int
    title: str
    document_type: str
    score: float
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    snippet: str = ""
    tickers: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    freshness: float = 1.0
    confidence: float = 0.5


class SearchResponse(BaseModel):
    query: str
    mode: str
    hits: list[SearchHit] = Field(default_factory=list)
    knowledge_version: str = "kip-v1.0.1"


class RagEvidenceItem(BaseModel):
    document_id: str
    title: str
    snippet: str
    tickers: list[str] = Field(default_factory=list)
    stance: str = "neutral"  # bull / bear / neutral
    priority: int = 7
    source_class: str = "general"
    freshness: float = 1.0
    confidence: float = 0.5
    date: _dt.date | None = None


class RagEvidencePack(BaseModel):
    query: str
    documents_retrieved: list[str] = Field(default_factory=list)
    supporting_evidence: list[RagEvidenceItem] = Field(default_factory=list)
    conflicting_opinions: list[RagEvidenceItem] = Field(default_factory=list)
    source_list: list[str] = Field(default_factory=list)
    agi_research_used: list[str] = Field(default_factory=list)
    broker_reports_used: list[str] = Field(default_factory=list)
    news_used: list[str] = Field(default_factory=list)
    filings_used: list[str] = Field(default_factory=list)
    engine_evidence: list[dict[str, Any]] = Field(default_factory=list)
    l4_opinion: dict[str, Any] | None = None
    portfolio_exposure: dict[str, Any] | None = None
    freshness_score: float = 0.0
    confidence_score: float = 0.0
    last_updated: _dt.datetime | None = None
    knowledge_version: str = "kip-v1.0.1-p1"
    answer_policy: str = "retrieval_augmented_only"
    retrieval_order: list[str] = Field(
        default_factory=lambda: [
            "agi_research",
            "engine_states",
            "l4_opinion",
            "broker_research",
            "latest_news",
            "company_filings",
            "general_knowledge",
        ]
    )


class IngestRequest(BaseModel):
    title: str = ""
    content: str = ""
    author: str = ""
    source: str = "agi"
    document_type: DocumentType = DocumentType.OTHER
    broker: str = ""
    language: str = "en"
    date: _dt.date | None = None
    tickers: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    needs_ocr: bool = False
    ocr_text: str = ""
    lineage_id: str | None = None
    supersedes: str | None = None
    article_id: str | None = None
    research_type: str = ""
    time_horizon: str = ""
    expected_return: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BulkIngestItem(BaseModel):
    filename: str = ""
    content: str = ""  # decoded text or raw markdown/email body
    content_base64: str = ""
    mime_type: str = ""
    broker: str = ""
    title: str = ""
    tickers: list[str] = Field(default_factory=list)
    date: _dt.date | None = None
    needs_ocr: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class BulkIngestRequest(BaseModel):
    items: list[BulkIngestItem] = Field(default_factory=list)
    zip_base64: str = ""  # optional ZIP batch
    default_broker: str = ""
    source_channel: Literal["broker", "newsletter", "internal", "agi"] = "broker"


class ChannelIngestRequest(IngestRequest):
    """Single-document or bulk payload for channel ingest endpoints."""

    items: list[BulkIngestItem] = Field(default_factory=list)
    zip_base64: str = ""
    default_broker: str = ""


class BulkIngestResult(BaseModel):
    ingested: list[str] = Field(default_factory=list)
    failed: list[dict[str, str]] = Field(default_factory=list)
    count: int = 0


class HistoricalView(BaseModel):
    document_id: str
    version: int
    date: _dt.date | None = None
    thesis: str = ""
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    valuation: str = ""
    target_prices: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    article_id: str | None = None


class HouseView(BaseModel):
    ticker: str
    current_view: HistoricalView | None = None
    historical_views: list[HistoricalView] = Field(default_factory=list)
    thesis_evolution: list[str] = Field(default_factory=list)
    what_changed: list[str] = Field(default_factory=list)
    what_remained_correct: list[str] = Field(default_factory=list)
    failed_assumptions: list[str] = Field(default_factory=list)
    catalysts_occurred: list[str] = Field(default_factory=list)
    research_confidence: float = 0.0
    prediction_accuracy: float | None = None
    last_updated: _dt.datetime | None = None
    knowledge_version: str = "kip-v1.0.1-p1"


class ResearchHistory(BaseModel):
    ticker: str
    agi_reports: list[HistoricalView] = Field(default_factory=list)
    broker_reports: list[HistoricalView] = Field(default_factory=list)
    timeline: ResearchTimeline | None = None


class PredictionRecord(BaseModel):
    prediction_id: str = Field(default_factory=lambda: _new_id("pred"))
    ticker: str
    document_id: str
    article_id: str | None = None
    thesis: str = ""
    target_price: str = ""
    expected_return: str = ""
    catalysts: list[str] = Field(default_factory=list)
    sector: str = ""
    analyst: str = ""
    predicted_at: _dt.date
    horizon_days: int = 90
    status: Literal["open", "evaluated_3m", "evaluated_6m", "evaluated_12m"] = "open"
    outcome_return: float | None = None
    hit: bool | None = None
    thesis_success: bool | None = None
    catalyst_hit: bool | None = None
    evaluated_at: _dt.date | None = None
    notes: str = ""


class PredictionEvalRequest(BaseModel):
    prediction_id: str
    outcome_return: float
    thesis_success: bool | None = None
    catalyst_hit: bool | None = None
    as_of: _dt.date | None = None
    notes: str = ""


class PredictionStats(BaseModel):
    ticker: str | None = None
    predictions: int = 0
    evaluated: int = 0
    hit_rate: float | None = None
    average_return: float | None = None
    thesis_success_rate: float | None = None
    catalyst_accuracy: float | None = None
    sector_accuracy: dict[str, float] = Field(default_factory=dict)
    analyst_accuracy: dict[str, float] = Field(default_factory=dict)


class CompanyDossier(BaseModel):
    ticker: str
    house_view: HouseView | None = None
    research_history: ResearchHistory | None = None
    predictions: list[PredictionRecord] = Field(default_factory=list)
    prediction_stats: PredictionStats | None = None
    timeline: ResearchTimeline | None = None
    graph: KnowledgeGraphView | None = None
    knowledge_version: str = "kip-v1.0.1-p1"


class ClientSearchRequest(BaseModel):
    question: str
    ticker: str | None = None
    engine_states: list[dict[str, Any]] = Field(default_factory=list)
    l4_opinion: dict[str, Any] | None = None
    portfolio_exposure: dict[str, Any] | None = None


class ClientSearchResponse(BaseModel):
    """Homepage search NEVER answers directly — returns evidence for LLM synthesis."""

    question: str
    intent: str
    answer_policy: str = "never_answer_directly"
    evidence: RagEvidencePack
    house_view: HouseView | None = None
    validation: dict[str, Any] = Field(default_factory=dict)


class CompanyKnowledge(BaseModel):
    ticker: str
    documents: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    related_companies: list[str] = Field(default_factory=list)
    latest_thesis: str = ""
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    timeline: ResearchTimeline | None = None
    graph: KnowledgeGraphView | None = None


class ThemeKnowledge(BaseModel):
    theme_id: str
    theme: str
    documents: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    related_themes: list[str] = Field(default_factory=list)
