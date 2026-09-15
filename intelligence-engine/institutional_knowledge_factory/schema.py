"""Institutional Knowledge Factory (IKF) v1.0 — schema constants."""

from __future__ import annotations

from typing import Any

IKF_VERSION = "ikf-v1.0.0"
KPE_VERSION = IKF_VERSION  # Knowledge Production Engine alias
PROGRAMME = "AGI Knowledge Production Engine — Compile + Incremental Modes"
MODULE_CODE = "KPE"
LEGACY_MODULE_CODE = "IKF"

EXECUTION_MODES: tuple[str, ...] = ("compile", "incremental")

# Incremental mode pipeline (live evidence ingestion)
PIPELINE_STEPS: tuple[str, ...] = (
    "collect",
    "normalize",
    "extract",
    "identify_claims",
    "validate_evidence",
    "resolve_contradictions",
    "update_assertions",
    "update_company_dna",
    "update_monitoring",
    "version_decision_memory",
    "notify_research_workflows",
)

# Compile mode pipeline (historical / backfill)
COMPILE_PIPELINE_STEPS: tuple[str, ...] = (
    "collect",
    "normalize",
    "merge",
    "resolve_duplicates",
    "resolve_contradictions",
    "identify_assertions",
    "score_assertions",
    "link_evidence",
    "generate_company_dna",
    "generate_monitoring",
    "generate_thesis",
    "update_knowledge_object",
)

SOURCE_TYPES: tuple[str, ...] = (
    "annual_report",
    "quarterly_results",
    "investor_presentation",
    "conference_call",
    "corporate_filing",
    "exchange_announcement",
    "shareholding_data",
    "financial_statement",
    "consensus_estimate",
    "historical_price",
    "corporate_action",
    "macro_data",
    "sector_data",
    "alternative_data",
    "analyst_research",
)

SOURCE_TRUST_BASELINE: dict[str, int] = {
    "annual_report": 90,
    "quarterly_results": 85,
    "investor_presentation": 80,
    "conference_call": 75,
    "corporate_filing": 88,
    "exchange_announcement": 82,
    "shareholding_data": 85,
    "financial_statement": 90,
    "consensus_estimate": 70,
    "historical_price": 75,
    "corporate_action": 85,
    "macro_data": 80,
    "sector_data": 78,
    "alternative_data": 65,
    "analyst_research": 72,
}

APPROVED_WRITERS: tuple[str, ...] = (
    "evidence_pipeline",
    "workflow_completion",
    "monitoring_engine",
    "manual_analyst_review",
)

THESIS_COMPONENTS: tuple[str, ...] = (
    "current_thesis",
    "bull_thesis",
    "bear_thesis",
    "key_assumptions",
    "unknowns",
    "invalidation_conditions",
)

QUALITY_METRICS: tuple[str, ...] = (
    "knowledge_coverage",
    "assertion_coverage",
    "evidence_coverage",
    "freshness",
    "contradiction_count",
    "unknown_count",
    "data_quality",
    "review_status",
)

REVIEW_QUESTIONS: tuple[str, ...] = (
    "what_do_we_now_know",
    "what_changed",
    "what_became_stronger",
    "what_became_weaker",
    "what_became_uncertain",
    "what_should_be_monitored",
    "what_research_should_be_updated",
)
