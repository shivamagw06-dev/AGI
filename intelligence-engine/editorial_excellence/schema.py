"""Editorial Excellence Program v1.0 — schema and constants."""

from __future__ import annotations

PROGRAM_VERSION = "1.0"
PROGRAMME = "AGI Editorial Excellence Program"
LAYER = "Institutional Research Engine (IRE)"
ARCHITECTURE_STATUS = "Architecture Freeze v1.0 — communication improvement only"

FORWARD_RATINGS: tuple[str, ...] = (
    "YES",
    "MINOR_EDITS",
    "MAJOR_EDITS",
    "REWRITE",
)

SUCCESS_FORWARD_YES_PCT = 90.0
EDITORIAL_PASS_THRESHOLD = 90.0

# Editorial scorecard — aligned with Institutional Investor Curriculum v1.0
EDITORIAL_SCORECARD: tuple[str, ...] = (
    "clarity",
    "institutional_tone",
    "business_understanding",
    "investment_insight",
    "evidence_integration",
    "narrative_flow",
    "explanation_quality",
    "portfolio_relevance",
    "investor_usefulness",
    "forward_without_editing",
    "overall_editorial_score",
)

# Legacy dimensions retained for IWC section scoring (internal)
IWC_SCORECARD: tuple[str, ...] = (
    "executive_summary_quality",
    "investment_debate_quality",
    "questions_before_you_decide",
    "prioritization",
    "uncertainty_handling",
)

from institutional_investor_curriculum.schema import (
    HALL_OF_FAME_COUNT,
    TARGET_BENCHMARK_COUNT,
    UNIVERSAL_QUESTION_COUNT,
)

COMMON_WRITING_PROBLEMS: tuple[str, ...] = (
    "executive_summary_too_generic",
    "investment_debate_unclear",
    "evidence_repetitive",
    "too_many_facts",
    "too_little_explanation",
    "weak_conclusion",
    "poor_transitions",
    "mechanical_wording",
    "long_paragraphs",
    "passive_voice",
    "missing_uncertainty",
    "prohibited_recommendation_language",
)

PREFERRED_STYLE: tuple[str, ...] = (
    "The central investment debate",
    "Current evidence indicates",
    "The primary uncertainty",
    "Future value creation depends on",
    "Historical evidence suggests",
)

AVOID_STYLE: tuple[str, ...] = (
    "good company",
    "bad company",
    "strong buy",
    "cheap stock",
    "excellent returns",
    "huge upside",
    "bullish",
    "bearish",
)
