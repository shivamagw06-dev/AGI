"""IST-02 — Raw Evidence Institutional Research Validation."""

from __future__ import annotations

from typing import Any

IST02_WORKSTREAM_ID = "IST-02"
IST02_CASE_ID = "IST-02"
IST02_SPEC = "docs/AGI_IST_02_RAW_EVIDENCE_VALIDATION.md"
IST02_VERSION = "ist-02-v1.0.0"
IST02_PASS_SCORE = 85.0

IST02_ALLOWED_MODULES: tuple[str, ...] = (
    "FSE",
    "FIL",
    "FIRE-01",
    "FIRE-02",
    "FIRE-03",
    "FIRE-04",
    "FIRE-05",
    "FIRE-06",
    "IO-01",
    "CIO-01",
    "CW-01",
    "WO-01",
    "OfficeSDK",
    "PEB-01",
)

IST02_REPORT_SECTIONS: tuple[str, ...] = (
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
    "outstanding_unknowns",
    "monitoring_framework",
    "confidence_discussion",
    "evidence_appendix",
    "counterfactual_analysis",
)

IST02_RUBRIC_WEIGHTS: dict[str, float] = {
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

IST02_FAILURE_CODES: tuple[str, ...] = (
    "UNSUPPORTED_CONCLUSION",
    "NO_COUNTER_EVIDENCE",
    "NO_UNKNOWNS",
    "NO_MONITORING_FRAMEWORK",
    "PROVENANCE_MISSING",
    "CONFIDENCE_UNJUSTIFIED",
    "HALLUCINATED_FACT",
    "PEER_ANALYSIS_MISSING",
    "EVIDENCE_CHAIN_BROKEN",
    "FIXTURE_ANSWER_USED",
    "RAW_CORPUS_EMPTY",
)

IST02_EVIDENCE_TYPES: tuple[str, ...] = (
    "financial_statement",
    "annual_report",
    "quarterly_report",
    "earnings_call",
    "investor_presentation",
    "regulatory_filing",
    "exchange_announcement",
    "corporate_action",
    "historical_price",
    "peer_financial",
)

IST02_FREEZE_LOCKS: dict[str, Any] = {
    "raw_evidence_only": True,
    "no_fixture_answers": True,
    "no_prewritten_conclusions": True,
    "no_new_intelligence_engine": True,
    "reuse_existing_modules_only": True,
    "deterministic_scoring": True,
    "soft_wire_only": True,
    "pass_score": IST02_PASS_SCORE,
}
