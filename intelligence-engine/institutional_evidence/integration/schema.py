"""KIL-01 constants — Knowledge Integration Layer."""

from __future__ import annotations

KIL_WORKSTREAM_ID = "KIL-01"
KIL_PRODUCT = "Knowledge Integration Layer"
KIL_VERSION = "kil-01-v1.0.0"
KIL_SPEC = "docs/AGI_KIL_01_KNOWLEDGE_INTEGRATION_LAYER.md"

MISSION_STATEMENT = (
    "AGI operates as a Knowledge Operating System. Continuous Gather → Learn "
    "acquires institutional information. The Knowledge Integration Layer "
    "transforms that information into canonical institutional knowledge. "
    "The Institutional Evidence Platform validates, versions, and preserves "
    "that knowledge. All intelligence engines consume canonical knowledge — "
    "not raw providers."
)

# Phase-1 demo companies for end-to-end automation proof
KIL_PHASE1_DEMO = (
    "RELIANCE",
    "HDFCBANK",
    "TCS",
    "INFY",
    "ICICIBANK",
)

CGL_EVENT_TYPES = (
    "KnowledgeCollected",
    "FinancialStatementsUpdated",
    "AnnualReportDownloaded",
    "TranscriptAvailable",
    "CorporateActionDetected",
    "ShareholdingUpdated",
    "MacroSeriesUpdated",
    "ForecastCalibrated",
)

COVERAGE_STATES = (
    "DISCOVERED",
    "ACQUIRING",
    "NORMALIZING",
    "VALIDATING",
    "KNOWLEDGE READY",
    "RESEARCH READY",
    "INSTITUTIONAL COVERAGE COMPLETE",
    "CONTINUOUS MONITORING",
)

KNOWLEDGE_CONFIDENCE_WEIGHTS = {
    "financial_coverage": 20,
    "evidence_coverage": 15,
    "timeline_completeness": 10,
    "management_coverage": 10,
    "segment_coverage": 10,
    "transcript_coverage": 10,
    "valuation_coverage": 10,
    "historical_depth": 10,
    "freshness": 5,
}

KNOWLEDGE_CONFIDENCE_THRESHOLD = 70.0
KNOWLEDGE_LATENCY_TARGET_MINUTES = 15
COLLECTOR_SUCCESS_TARGET = 99.0

# Expansion: after Top-20 Institutional Coverage Complete → next Nifty 500
EXPANSION_NEXT_UNIVERSE = "nifty_500"
EXPANSION_NEXT_SIZE = 500
EXPANSION_REQUIRES_STATE = "INSTITUTIONAL COVERAGE COMPLETE"
