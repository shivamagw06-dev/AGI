"""ICF-01 — Institutional Coverage Factory constants.

Target is companies/day reaching Institutional Coverage Complete (ICC),
not shallow crawl throughput.
"""

from __future__ import annotations

from enum import Enum

ICF_WORKSTREAM_ID = "ICF-01"
ICF_PRODUCT = "Institutional Coverage Factory"
ICF_VERSION = "icf-01-v1.0.0"
ICF_SPEC = "docs/AGI_ICF_01_INSTITUTIONAL_COVERAGE_FACTORY.md"

MISSION = (
    "Build a factory that continuously drives companies toward Institutional "
    "Coverage Complete (ICC). Every company progresses through the same "
    "pipeline automatically, 24×7."
)

PIPELINE = (
    "Universe",
    "Coverage Planner",
    "Acquire Missing Evidence",
    "Normalize",
    "Validate",
    "Evidence Registry",
    "Company Memory",
    "Knowledge Graph",
    "Research Readiness",
    "Institutional Coverage Complete",
)

# Required evidence classes (weights sum = 100)
EVIDENCE_CLASSES = {
    "annual_reports": {
        "required": True,
        "weight": 10,
        "collector": "annual_reports",
        "document_types": ("annual_report",),
        "phase1_keys": ("complete_annual_reports",),
    },
    "quarterly_results": {
        "required": True,
        "weight": 10,
        "collector": "quarterly_results",
        "document_types": ("quarterly_results",),
        "phase1_keys": ("quarterly_history",),
    },
    "financial_statements": {
        "required": True,
        "weight": 20,
        "collector": "quarterly_results",
        "document_types": ("nse_xbrl", "quarterly_results", "annual_report"),
        "phase1_keys": ("financial_statements_10y", "canonical_financials"),
    },
    "earnings_presentations": {
        "required": True,
        "weight": 10,
        "collector": "investor_presentations",
        "document_types": ("earnings_presentation",),
        "phase1_keys": ("earnings_presentations",),
    },
    "earnings_call_transcripts": {
        "required": True,
        "weight": 10,
        "collector": "transcripts",
        "document_types": ("earnings_transcript", "earnings_call_transcript"),
        "phase1_keys": ("earnings_call_transcripts",),
    },
    "shareholding": {
        "required": True,
        "weight": 10,
        "collector": "shareholding",
        "document_types": ("shareholding",),
        "phase1_keys": ("shareholding_history",),
    },
    "corporate_actions": {
        "required": True,
        "weight": 5,
        "collector": "corporate_actions",
        "document_types": ("corporate_action",),
        "phase1_keys": ("corporate_actions",),
    },
    "management_guidance": {
        "required": True,
        "weight": 5,
        "collector": "guidance",
        "document_types": ("management_guidance", "guidance"),
        "phase1_keys": (),  # soft — presence of guidance docs or earnings pack guidance
    },
    "segment_kpis": {
        "required": True,
        "weight": 10,
        "collector": "segment_data",
        "document_types": ("segment_data",),
        "phase1_keys": ("segment_history",),
    },
    "company_memory": {
        "required": True,
        "weight": 5,
        "collector": None,
        "document_types": (),
        "phase1_keys": ("company_memory",),
    },
    "knowledge_graph": {
        "required": True,
        "weight": 5,
        "collector": None,
        "document_types": (),
        "phase1_keys": ("knowledge_graph",),
    },
}


class PriorityTier(str, Enum):
    TOP20 = "TOP20"
    NIFTY50 = "NIFTY50"
    NIFTY100 = "NIFTY100"
    UNIVERSE = "UNIVERSE"


PRIORITY_TIERS = tuple(t.value for t in PriorityTier)

# Default config — scalable without redesign (companies entering ICC / day)
DEFAULT_CONFIG = {
    "enabled": True,
    "max_companies_per_day": 100,  # ICC entries / day target — not crawl count
    "max_parallel_collectors": 20,
    "tick_interval_minutes": 15,
    "planner_interval_minutes": 15,
    "companies_per_tick": 8,
    "priority": list(PRIORITY_TIERS),
    "retry_policy": {
        "max_attempts": 5,
        "backoff_seconds": [60, 300, 900, 3600, 7200],
    },
    "coverage_threshold": 90.0,  # operational progress gate
    "institutional_coverage_threshold": 100.0,  # ICC requires full mandatory set
    "research_readiness_threshold": 70.0,
    "research_ready_threshold": 70.0,
    "knowledge_confidence_threshold": 70.0,
}

ICC_EXIT_CRITERIA = (
    "all_mandatory_evidence_present",
    "canonical_financials_published",
    "evidence_registry_complete",
    "company_memory_populated",
    "knowledge_graph_refreshed",
    "research_readiness_above_threshold",
    "knowledge_confidence_above_threshold",
    "claim_safe",
    "research_note_traceable",
)

FACTORY_STATUS = (
    "NOT_STARTED",
    "QUEUED",
    "IN_PROGRESS",
    "BLOCKED",
    "ICC_COMPLETE",
    "MONITORING",
)
