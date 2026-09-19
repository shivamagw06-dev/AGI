"""IRP V1 domain models — orchestration artefacts only (no KIP/RSP redesign)."""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _new_id(prefix: str = "irp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


IntentType = Literal[
    "company_research",
    "sector_research",
    "theme_research",
    "macro_research",
    "portfolio_construction",
    "valuation",
    "compare_companies",
    "risk_analysis",
    "earnings_analysis",
    "prediction",
    "market_outlook",
    "investment_thesis",
    "event_impact",
    "general_finance_education",
    "news_explanation",
    "screening",
    "general_research",
]

DomainType = Literal[
    "company",
    "sector",
    "theme",
    "macro",
    "commodity",
    "currency",
    "market",
    "portfolio",
    "event",
    "earnings",
    "valuation",
    "risk",
]


class ResolvedEntityPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sector_key: str | None = None
    sector_label: str | None = None
    sector: str | None = None
    companies: list[dict[str, str]] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    currencies: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    macro_drivers: list[str] = Field(default_factory=list)
    reject_topics: list[str] = Field(default_factory=list)
    primary_ticker: str | None = None


class ResearchPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int
    source_class: str
    query: str
    required: bool = True
    rationale: str = ""


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(default_factory=lambda: _new_id("plan"))
    intent: str
    domain: str
    steps: list[ResearchPlanStep] = Field(default_factory=list)
    focus_tickers: list[str] = Field(default_factory=list)
    focus_themes: list[str] = Field(default_factory=list)
    reject_topics: list[str] = Field(default_factory=list)


class RankedEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str | None = None
    title: str = ""
    snippet: str = ""
    source_class: str = "general"
    stance: str = "neutral"
    relevance_score: float = 0.0
    freshness: float = 0.0
    reliability: float = 0.0
    coverage: float = 0.0
    confidence: float = 0.0
    tickers: list[str] = Field(default_factory=list)
    rejected: bool = False
    reject_reason: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ContradictionNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    summary: str
    why: str = ""
    sides: list[str] = Field(default_factory=list)
    confidence: float | None = None


class InstitutionalReasoning(BaseModel):
    """Internal reasoning package — constructed BEFORE answer generation."""

    model_config = ConfigDict(extra="forbid")

    what_is_happening: str = ""
    why: str = ""
    what_changed: str = ""
    why_it_matters: str = ""
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    uncertainties: list[str] = Field(default_factory=list)
    stance: str = "Neutral"
    outlook: str = ""
    key_drivers: list[str] = Field(default_factory=list)
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    neutral_case: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    valuation_perspective: str = ""
    macro_drivers: list[str] = Field(default_factory=list)
    sector_drivers: list[str] = Field(default_factory=list)
    company_leaders: list[str] = Field(default_factory=list)
    historical_comparison: str = ""


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answered_question: bool = True
    unrelated_evidence: bool = False
    missing_major_companies: bool = False
    missing_major_drivers: bool = False
    confidence_justified: bool = True
    internally_consistent: bool = True
    issues: list[str] = Field(default_factory=list)
    rebuilt: bool = False
    passed: bool = True


class LearningRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(default_factory=lambda: _new_id("learn"))
    question: str
    intent: str
    domain: str
    entities: dict[str, Any] = Field(default_factory=dict)
    research_plan: dict[str, Any] = Field(default_factory=dict)
    evidence_used: list[str] = Field(default_factory=list)
    rejected_evidence: list[str] = Field(default_factory=list)
    final_reasoning: dict[str, Any] = Field(default_factory=dict)
    follow_ups: list[str] = Field(default_factory=list)
    quality_score: float = 0.0
    created_at: _dt.datetime = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))


class IrpPackage(BaseModel):
    """Full IRP output consumed by Ask AGI / UiService (never raw engine names)."""

    model_config = ConfigDict(extra="forbid")

    irp_id: str = Field(default_factory=lambda: _new_id("irp"))
    version: str = "irp-v1.0.0"
    architecture_status: str = "v1.0.1 LOCKED"
    question: str
    intent: str
    domain: str
    entities: ResolvedEntityPack = Field(default_factory=ResolvedEntityPack)
    research_plan: ResearchPlan | None = None
    ranked_evidence: list[RankedEvidenceItem] = Field(default_factory=list)
    rejected_evidence: list[RankedEvidenceItem] = Field(default_factory=list)
    contradictions: list[ContradictionNote] = Field(default_factory=list)
    reasoning: InstitutionalReasoning = Field(default_factory=InstitutionalReasoning)
    validation: ValidationReport = Field(default_factory=ValidationReport)
    # Soft-pass through existing platform artefacts (unchanged contracts)
    client_search: dict[str, Any] = Field(default_factory=dict)
    house_view: dict[str, Any] | None = None
    rsp: dict[str, Any] = Field(default_factory=dict)
    follow_ups: list[str] = Field(default_factory=list)
    institutional_briefing: dict[str, Any] = Field(default_factory=dict)
    # IRP sector pack + optional SIF v1.0 provenance under key "sif" (additive)
    sector_intelligence: dict[str, Any] = Field(default_factory=dict)
    company_intelligence: dict[str, Any] = Field(default_factory=dict)
    # FAPI v1.0 — Finance Academy provenance for production reasoning (additive)
    finance_academy: dict[str, Any] = Field(default_factory=dict)
    # LEO v1.0 — Live Evidence Orchestrator provenance (additive)
    live_evidence: dict[str, Any] = Field(default_factory=dict)
    answer_policy: str = "think_then_answer_institutional"
    created_at: _dt.datetime = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
