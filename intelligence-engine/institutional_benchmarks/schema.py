"""IBS-01 — AGI Institutional Benchmark Suite."""

from __future__ import annotations

from typing import Any

IBS_WORKSTREAM_ID = "IBS-01"
IBS_PRODUCT = "AGI Institutional Benchmark Suite"
IBS_VERSION = "ibs-01-v1.0.0"
IBS_SUBSYSTEM = "institutional_benchmarks"
IBS_SPEC = "docs/AGI_IBS_01_INSTITUTIONAL_BENCHMARK_SUITE.md"
IBS_PROGRAMME = "AGI Intelligence Core Benchmarks"

PASS_SCORE = 85.0
RELEASE_MIN_AVERAGE = 85.0

SECTORS: tuple[str, ...] = (
    "BANKING",
    "IT",
    "PHARMA",
    "INDUSTRIALS",
    "ENERGY",
    "CONSUMER",
    "FINANCIAL_EVENTS",
    "MACRO",
)

REPORT_SECTIONS: tuple[str, ...] = (
    "executive_summary",
    "historical_timeline",
    "what_happened",
    "business_context",
    "financial_analysis",
    "business_quality",
    "management_assessment",
    "evidence_supporting",
    "evidence_contradicting",
    "alternative_interpretations",
    "peer_comparison",
    "historical_context",
    "risk_assessment",
    "outstanding_unknowns",
    "monitoring_framework",
    "confidence_discussion",
    "evidence_appendix",
    "counterfactual_analysis",
)

RUBRIC_WEIGHTS: dict[str, float] = {
    "research_structure": 10.0,
    "financial_reasoning": 15.0,
    "business_reasoning": 15.0,
    "evidence_quality": 15.0,
    "counter_evidence": 10.0,
    "confidence_calibration": 10.0,
    "peer_comparison": 10.0,
    "monitoring_framework": 5.0,
    "source_traceability": 10.0,
    "institutional_writing_quality": 10.0,
}

FAILURE_CODES: tuple[str, ...] = (
    "UNSUPPORTED_CONCLUSION",
    "PROVENANCE_MISSING",
    "NO_COUNTER_EVIDENCE",
    "NO_UNKNOWNS",
    "NO_MONITORING_FRAMEWORK",
    "NO_PEER_ANALYSIS",
    "NO_TIMELINE",
    "CONFIDENCE_UNJUSTIFIED",
    "HALLUCINATED_FACT",
    "EVIDENCE_CHAIN_BROKEN",
    "RAW_EVIDENCE_NOT_USED",
    "FIXTURE_ANSWER_USED",
    "CONSISTENCY_FAILURE",
    "RAW_CORPUS_EMPTY",
)

FREEZE_LOCKS: dict[str, Any] = {
    "raw_evidence_only": True,
    "no_fixture_answers": True,
    "no_prewritten_research": True,
    "no_new_intelligence_engine": True,
    "reuse_existing_modules_only": True,
    "soft_wire_only": True,
    "deterministic_scoring": True,
    "pass_score": PASS_SCORE,
    "release_min_average": RELEASE_MIN_AVERAGE,
}

CI_RELEASE_GATES: dict[str, Any] = {
    "average_score_min": RELEASE_MIN_AVERAGE,
    "hallucinations_max": 0,
    "broken_provenance_max": 0,
    "unsupported_conclusions_max": 0,
    "consistency_failures_max": 0,
}
