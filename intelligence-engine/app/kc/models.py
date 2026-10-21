"""KCV1 corpus models — quality, gaps, learning, executive metrics."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


GapSeverity = Literal["critical", "high", "medium", "low"]
GapKind = Literal[
    "weak_company_coverage",
    "stale_research",
    "missing_earnings",
    "missing_annual_report",
    "missing_investor_presentation",
    "outdated_sector_dossier",
    "low_confidence",
    "conflicting_knowledge",
    "missing_theme_view",
    "missing_macro_view",
]


class KnowledgeQualityScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_kind: str
    object_key: str
    coverage_score: float = 0.0
    confidence_score: float = 0.0
    freshness_score: float = 0.0
    evidence_score: float = 0.0
    consistency_score: float = 0.0
    completeness_score: float = 0.0
    recency_score: float = 0.0
    overall_quality: float = 0.0


class GapTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    kind: GapKind
    severity: GapSeverity
    object_kind: str
    object_key: str
    title: str
    detail: str = ""
    suggested_action: str = ""
    created_at: str = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat())


class LearningDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    learned_today: list[str] = Field(default_factory=list)
    what_changed: list[str] = Field(default_factory=list)
    companies_changed: list[str] = Field(default_factory=list)
    sectors_changed: list[str] = Field(default_factory=list)
    themes_changed: list[str] = Field(default_factory=list)
    macro_changed: list[str] = Field(default_factory=list)
    predictions_improved: list[str] = Field(default_factory=list)
    predictions_weakened: list[str] = Field(default_factory=list)
    research_to_update: list[str] = Field(default_factory=list)
    documents_processed: int = 0


class CorpusMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    programme: str = "KCV1"
    architecture_status: str = "v1.0.1 LOCKED"
    nifty_50_coverage: float = 0.0
    nifty_50_covered: int = 0
    nifty_50_total: int = 0
    nifty_next_50_coverage: float = 0.0
    nifty_next_50_covered: int = 0
    nifty_500_path_coverage: float = 0.0
    nifty_500_path_covered: int = 0
    nifty_500_path_total: int = 0
    companies_covered: int = 0
    sector_coverage: int = 0
    theme_coverage: int = 0
    macro_coverage: int = 0
    research_notes: int = 0
    broker_reports: int = 0
    predictions: int = 0
    knowledge_objects: int = 0
    relationships: int = 0
    avg_freshness: float = 0.0
    avg_confidence: float = 0.0
    avg_quality: float = 0.0
    research_structured: int = 0
    predictions_structured: int = 0
    gaps_open: int = 0
    needs_attention: int = 0
    recently_updated: list[dict[str, Any]] = Field(default_factory=list)
    coverage_heatmap: list[dict[str, Any]] = Field(default_factory=list)
    last_populated_at: str | None = None
