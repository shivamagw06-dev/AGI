"""KF1 knowledge object schemas — structured institutional knowledge."""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _new_id(prefix: str = "kf") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


KnowledgeKind = Literal["company", "sector", "theme", "macro", "prediction", "research_extract"]


class KnowledgeMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str = Field(default_factory=lambda: _new_id("kobj"))
    kind: KnowledgeKind
    key: str
    version: int = 1
    confidence: float = 0.4
    freshness: float = 1.0
    source_reliability: float = 0.7
    sources: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    created_at: _dt.datetime = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
    updated_at: _dt.datetime = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
    change_log: list[str] = Field(default_factory=list)


class CompanyKnowledgeObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: KnowledgeMeta
    company_name: str
    ticker: str
    sector: str = ""
    industry: str = ""
    sub_industry: str = ""
    business_description: str = ""
    products: list[str] = Field(default_factory=list)
    segments: list[str] = Field(default_factory=list)
    revenue_mix: list[str] = Field(default_factory=list)
    geographic_mix: list[str] = Field(default_factory=list)
    customers: list[str] = Field(default_factory=list)
    suppliers: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    promoters: list[str] = Field(default_factory=list)
    management: list[str] = Field(default_factory=list)
    shareholding: list[str] = Field(default_factory=list)
    financial_history: list[str] = Field(default_factory=list)
    margins: list[str] = Field(default_factory=list)
    roe: str = ""
    roce: str = ""
    debt: str = ""
    cash_flow: str = ""
    valuation: str = ""
    key_risks: list[str] = Field(default_factory=list)
    key_catalysts: list[str] = Field(default_factory=list)
    latest_thesis: str = ""
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    historical_house_views: list[dict[str, Any]] = Field(default_factory=list)
    predictions: list[dict[str, Any]] = Field(default_factory=list)
    related_research: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)


class SectorKnowledgeObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: KnowledgeMeta
    sector_id: str
    label: str
    definition: str = ""
    industry_structure: list[str] = Field(default_factory=list)
    growth_drivers: list[str] = Field(default_factory=list)
    demand_drivers: list[str] = Field(default_factory=list)
    supply_drivers: list[str] = Field(default_factory=list)
    cost_drivers: list[str] = Field(default_factory=list)
    key_metrics: list[str] = Field(default_factory=list)
    historical_cycles: list[str] = Field(default_factory=list)
    major_companies: list[dict[str, str]] = Field(default_factory=list)
    global_comparisons: list[str] = Field(default_factory=list)
    valuation_framework: str = ""
    current_agi_view: str = ""
    historical_house_views: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    latest_thesis: str = ""


class ThemeKnowledgeObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: KnowledgeMeta
    theme_id: str
    label: str
    definition: str = ""
    investment_thesis: str = ""
    companies: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    beneficiaries: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    macro_drivers: list[str] = Field(default_factory=list)
    historical_evolution: list[str] = Field(default_factory=list)
    current_agi_view: str = ""
    related_sectors: list[str] = Field(default_factory=list)


class MacroKnowledgeObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: KnowledgeMeta
    macro_id: str
    label: str
    definition: str = ""
    why_investors_care: str = ""
    affected_sectors: list[str] = Field(default_factory=list)
    affected_companies: list[str] = Field(default_factory=list)
    leading_indicators: list[str] = Field(default_factory=list)
    lagging_indicators: list[str] = Field(default_factory=list)
    historical_episodes: list[str] = Field(default_factory=list)
    current_agi_view: str = ""


class PredictionKnowledgeObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: KnowledgeMeta
    prediction_id: str
    prediction: str
    date: str | None = None
    company: str = ""
    sector: str = ""
    theme: str = ""
    confidence: float = 0.5
    expected_catalysts: list[str] = Field(default_factory=list)
    expected_timeline: str = ""
    expected_outcome: str = ""
    actual_outcome: str = ""
    lessons_learned: list[str] = Field(default_factory=list)
    status: str = "open"


class ResearchExtractObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: KnowledgeMeta
    document_id: str
    title: str = ""
    question: str = ""
    summary: str = ""
    investment_thesis: str = ""
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    neutral_case: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    valuation_view: str = ""
    time_horizon: str = ""
    confidence: float = 0.5
    prediction: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    macro_factors: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class KnowledgeSearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: KnowledgeKind
    key: str
    label: str
    score: float
    confidence: float
    freshness: float
    summary: str = ""
    object_id: str = ""


class KnowledgeCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    companies_covered: int = 0
    companies_seeded: int = 0
    sector_coverage: int = 0
    sectors_seeded: int = 0
    theme_coverage: int = 0
    themes_seeded: int = 0
    macro_coverage: int = 0
    macros_seeded: int = 0
    research_extracts: int = 0
    prediction_coverage: int = 0
    relationship_count: int = 0
    avg_confidence: float = 0.0
    avg_freshness: float = 0.0
    duplicate_reductions: int = 0
    last_updated: str | None = None
