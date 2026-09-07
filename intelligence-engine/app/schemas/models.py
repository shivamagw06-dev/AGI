from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "") -> str:
    value = uuid4().hex
    return f"{prefix}{value}" if prefix else value


class DeskType(str, Enum):
    SMOKE = "smoke"
    CIO_MORNING = "cio_morning"
    EQUITY = "equity"
    PORTFOLIO = "portfolio"
    INVESTMENT_OFFICE = "investment_office"
    CUSTOM = "custom"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SourceType(str, Enum):
    AGIB_CACHE = "agib_cache"
    MACRO = "macro"
    MARKET = "market"
    NEWS = "news"
    PRE_MARKET = "pre_market"
    FUNDAMENTAL = "fundamental"
    INTERNAL = "internal"
    MEMORY = "memory"
    PORTFOLIO = "portfolio"
    INVESTMENT_OFFICE = "investment_office"


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: new_id("ev_"))
    claim: str
    source_id: str
    source_type: SourceType
    fetched_at: datetime = Field(default_factory=utcnow)
    snippet: str | None = None
    url: str | None = None
    reliability: float = Field(default=0.7, ge=0.0, le=1.0)

    @field_validator("claim")
    @classmethod
    def claim_not_empty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Evidence claim cannot be empty")
        return text


class ConfidenceBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    supports: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    rationale: str

    @field_validator("rationale")
    @classmethod
    def rationale_required(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Confidence rationale is required")
        return text


class Finding(BaseModel):
    statement: str
    evidence_ids: list[str] = Field(min_length=1)
    is_scenario: bool = False
    confidence: int | None = Field(default=None, ge=0, le=100)


class AgentOutput(BaseModel):
    agent_id: str
    mission: str
    findings: list[Finding] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: ConfidenceBreakdown
    assumptions: list[str] = Field(default_factory=list)
    invalidators: list[str] = Field(default_factory=list)
    raw_trace_ref: str | None = None
    completed_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def evidence_must_back_findings(self) -> "AgentOutput":
        if not self.evidence:
            raise ValueError("AgentOutput requires at least one evidence item")
        known = {item.evidence_id for item in self.evidence}
        for finding in self.findings:
            missing = [eid for eid in finding.evidence_ids if eid not in known]
            if missing:
                raise ValueError(f"Finding cites unknown evidence ids: {missing}")
        return self


class DebatePosition(BaseModel):
    side: Literal["bull", "base", "bear"]
    points: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class DebatePackage(BaseModel):
    summary: str
    positions: list[DebatePosition] = Field(default_factory=list)
    unresolved_conflicts: list[str] = Field(default_factory=list)


class ScenarioCase(BaseModel):
    label: str
    probability: int = Field(ge=0, le=100)
    detail: str
    is_prediction: bool = True


class InstitutionalReport(BaseModel):
    report_id: str = Field(default_factory=lambda: new_id("rpt_"))
    desk: DeskType
    title: str
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    macro_view: str | None = None
    market_view: str | None = None
    sector_view: str | None = None
    company_view: str | None = None
    technical_view: str | None = None
    valuation_view: str | None = None
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    bull_case: ScenarioCase | None = None
    base_case: ScenarioCase | None = None
    bear_case: ScenarioCase | None = None
    confidence: ConfidenceBreakdown
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    citations: dict[str, list[str]] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=utcnow)


class DirectorPlan(BaseModel):
    desk: DeskType
    agent_ids: list[str]
    rationale: str
    require_all: bool = False


class ResearchRunCreate(BaseModel):
    desk: DeskType = DeskType.SMOKE
    query: str | None = None
    symbols: list[str] = Field(default_factory=list)
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PortfolioHolding(BaseModel):
    """Normalized holding — never invents prices or returns."""

    symbol: str
    weight: float | None = Field(default=None, ge=0.0, le=1.0)
    quantity: float | None = None
    avg_price: float | None = None
    sector: str | None = None
    name: str | None = None
    notes: str | None = None


class PortfolioSnapshot(BaseModel):
    portfolio_id: str = Field(default_factory=lambda: new_id("pf_"))
    name: str = "Client Portfolio"
    client_id: str | None = None
    source: Literal["manual", "csv", "model", "broker_future"] = "manual"
    holdings: list[PortfolioHolding] = Field(default_factory=list)
    currency: str = "INR"
    as_of: datetime = Field(default_factory=utcnow)
    notes: list[str] = Field(default_factory=list)


class PortfolioRecommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: new_id("rec_"))
    priority: Literal["high", "medium", "low"] = "medium"
    verb: Literal["Review", "Research", "Monitor", "Consider", "Investigate"] = "Review"
    title: str
    reason: str
    evidence: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)
    symbols: list[str] = Field(default_factory=list)
    supporting_research: list[str] = Field(default_factory=list)


class PortfolioPackage(BaseModel):
    """Portfolio Office package — packaging only; never executes trades or invents returns."""

    portfolio: PortfolioSnapshot
    health_score: int | None = Field(default=None, ge=0, le=100)
    research_score: int | None = Field(default=None, ge=0, le=100)
    forecast_score: int | None = Field(default=None, ge=0, le=100)
    risk_score: int | None = Field(default=None, ge=0, le=100)
    diversification_score: int | None = Field(default=None, ge=0, le=100)
    sector_exposure: dict[str, float] = Field(default_factory=dict)
    macro_exposure: dict[str, Any] = Field(default_factory=dict)
    holding_research: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[PortfolioRecommendation] = Field(default_factory=list)
    action_center: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    health_summary: dict[str, Any] = Field(default_factory=dict)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    monthly_report: dict[str, Any] = Field(default_factory=dict)
    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    monitoring: dict[str, Any] = Field(default_factory=dict)
    workspace: dict[str, Any] = Field(default_factory=dict)
    client_dashboard: dict[str, Any] = Field(default_factory=dict)
    advisor_dashboard: dict[str, Any] = Field(default_factory=dict)
    child_runs: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)
    notes: list[str] = Field(default_factory=list)
    withheld: list[str] = Field(default_factory=list)
    components_reused: list[str] = Field(default_factory=list)


class PortfolioIngestRequest(BaseModel):
    name: str = "Client Portfolio"
    client_id: str | None = None
    source: Literal["manual", "csv", "model", "broker_future"] = "manual"
    holdings: list[dict[str, Any]] = Field(default_factory=list)
    csv_text: str | None = None
    model_id: str | None = None


class ResearchQueueItem(BaseModel):
    item_id: str = Field(default_factory=lambda: new_id("rq_"))
    priority: Literal["high", "medium", "low"] = "medium"
    symbol: str | None = None
    title: str
    reason: str
    evidence: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)
    supporting_research: list[str] = Field(default_factory=list)
    related_reports: list[str] = Field(default_factory=list)


class CalendarEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("cal_"))
    category: Literal[
        "earnings",
        "rbi",
        "fed",
        "inflation",
        "gdp",
        "corporate_action",
        "agm",
        "dividend",
        "policy",
        "results",
        "other",
    ] = "other"
    title: str
    date: str | None = None
    status: Literal["scheduled", "tentative", "withheld"] = "withheld"
    evidence: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    note: str | None = None


class DecisionJournalEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: new_id("dj_"))
    kind: Literal[
        "research_completed",
        "forecast_revision",
        "portfolio_review",
        "watchlist_change",
        "scenario_analysis",
        "cio_recommendation",
        "other",
    ] = "other"
    title: str
    detail: str
    ts: datetime = Field(default_factory=utcnow)
    evidence: list[str] = Field(default_factory=list)
    confidence: int | None = Field(default=None, ge=0, le=100)
    related_run_id: str | None = None


class KnowledgeGraphNode(BaseModel):
    node_id: str
    label: str
    kind: Literal["company", "sector", "theme", "macro", "forecast", "research", "risk", "event", "playbook"]
    meta: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    evidence: list[str] = Field(default_factory=list)


class InvestmentOfficePackage(BaseModel):
    """Operational layer above existing AGI capabilities — packaging only."""

    office_id: str = Field(default_factory=lambda: new_id("io_"))
    as_of: datetime = Field(default_factory=utcnow)
    daily_brief: dict[str, Any] = Field(default_factory=dict)
    research_queue: list[ResearchQueueItem] = Field(default_factory=list)
    calendar: list[CalendarEvent] = Field(default_factory=list)
    playbooks: list[dict[str, Any]] = Field(default_factory=list)
    scenario_center: dict[str, Any] = Field(default_factory=dict)
    research_timeline: list[dict[str, Any]] = Field(default_factory=list)
    decision_journal: list[DecisionJournalEntry] = Field(default_factory=list)
    knowledge_graph: dict[str, Any] = Field(default_factory=dict)
    portfolio_office_link: dict[str, Any] = Field(default_factory=dict)
    workspace: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)
    notes: list[str] = Field(default_factory=list)
    withheld: list[str] = Field(default_factory=list)
    components_reused: list[str] = Field(default_factory=list)


class InvestmentOfficeRequest(BaseModel):
    """Inputs for Investment Office packaging — never invents market facts."""

    user_id: str | None = None
    watchlist: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    portfolio: PortfolioIngestRequest | None = None
    journal_seed: list[dict[str, Any]] = Field(default_factory=list)
    prior_runs: list[dict[str, Any]] = Field(default_factory=list)
    query: str | None = None


class ResearchRun(BaseModel):
    run_id: str = Field(default_factory=lambda: new_id("run_"))
    desk: DeskType
    status: RunStatus = RunStatus.QUEUED
    query: str | None = None
    symbols: list[str] = Field(default_factory=list)
    director_plan: DirectorPlan | None = None
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    debate: DebatePackage | None = None
    cio_thesis: str | None = None
    report: InstitutionalReport | None = None
    portfolio: PortfolioPackage | None = None
    investment_office: InvestmentOfficePackage | None = None
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class PredictionRecord(BaseModel):
    prediction_id: str = Field(default_factory=lambda: new_id("pred_"))
    run_id: str
    statement: str
    horizon: str
    created_at: datetime = Field(default_factory=utcnow)
    actual_outcome: str | None = None
    accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    success_reason: str | None = None
    failure_reason: str | None = None
