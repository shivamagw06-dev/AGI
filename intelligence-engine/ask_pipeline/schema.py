"""AGIB v2.1 Ask Pipeline schema — integration only; no reasoning redesign."""

from __future__ import annotations

from typing import Any

PIPELINE_VERSION = "ask-pipeline-v2.0.0"
PROGRAMME = "AGIB v3.4 – Ask Pipeline 2.0 (Intent Resolution)"
MODULE_CODE = "ASKP"

INTENTS: tuple[str, ...] = (
    "Education",
    "Research",
    "Valuation",
    "Comparison",
    "Accounting",
    "BusinessQuality",
    "Macro",
    "Government",
    "Industry",
    "Portfolio",
    "Risk",
    "Watchlist",
    "Screening",
    "Replay",
    "Historical",
    "Expectation",
    "AlternativeData",
    "Unknown",
)

ENTITY_TYPES: tuple[str, ...] = (
    "company",
    "sector",
    "industry",
    "commodity",
    "government_policy",
    "macro_variable",
    "alternative_dataset",
    "portfolio",
    "universe",
    "relationship",
    "timeline",
)

KNOWLEDGE_OBJECTS: tuple[str, ...] = (
    "universe",
    "company",
    "corporate_events",
    "government",
    "industry",
    "relationships",
    "alternative_data",
    "expectations",
    "historical",
    "decision_memory",
    "replay",
    "macro",
)

PACK_TYPES: tuple[str, ...] = (
    "company",
    "industry",
    "government",
    "relationship",
    "alternative_data",
    "expectation",
    "portfolio",
    "decision",
)

FREEZE_LOCKS: dict[str, Any] = {
    "phases_1_7": True,
    "knowledge_factory": True,
    "governance": True,
    "committee_system": True,
    "evidence_contracts": True,
    "decision_quality_scoring": True,
    "continuous_adaptive_learning": True,
    "soft_wire_only": True,
    "no_new_frameworks": True,
    "no_new_committees": True,
}

# Intent → KF object selection (True required attempt, "optional" soft)
KNOWLEDGE_SELECTION: dict[str, dict[str, str]] = {
    "Education": {"company": "optional"},
    "Valuation": {
        "company": "required",
        "corporate_events": "required",
        "industry": "optional",
        "government": "optional",
        "relationships": "optional",
        "expectations": "optional",
        "historical": "optional",
    },
    "Accounting": {
        "company": "required",
        "corporate_events": "optional",
        "historical": "optional",
    },
    "BusinessQuality": {
        "company": "required",
        "corporate_events": "required",
        "industry": "optional",
        "relationships": "optional",
    },
    "Comparison": {
        "company": "required",
        "corporate_events": "required",
        "industry": "required",
        "relationships": "required",
        "universe": "required",
        "expectations": "optional",
    },
    "Industry": {
        "company": "required",
        "industry": "required",
        "relationships": "required",
        "government": "optional",
    },
    "Government": {
        "government": "required",
        "relationships": "optional",
        "macro": "optional",
        "company": "optional",
    },
    "Macro": {
        "macro": "required",
        "government": "optional",
        "relationships": "optional",
        "alternative_data": "optional",
    },
    "AlternativeData": {
        "alternative_data": "required",
        "company": "required",
        "relationships": "required",
        "expectations": "optional",
        "macro": "optional",
    },
    "Expectation": {
        "expectations": "required",
        "company": "required",
        "alternative_data": "optional",
        "relationships": "optional",
    },
    "Portfolio": {
        "company": "required",
        "corporate_events": "required",
        "expectations": "required",
        "industry": "optional",
        "relationships": "optional",
        "alternative_data": "optional",
        "universe": "optional",
        "decision_memory": "optional",
    },
    "Risk": {
        "company": "required",
        "corporate_events": "required",
        "expectations": "required",
        "relationships": "optional",
    },
    "Research": {
        "company": "required",
        "corporate_events": "optional",
        "industry": "optional",
        "expectations": "optional",
    },
    "Historical": {
        "company": "required",
        "historical": "required",
        "corporate_events": "required",
        "decision_memory": "optional",
        "replay": "optional",
    },
    "Replay": {
        "company": "required",
        "historical": "required",
        "decision_memory": "required",
        "replay": "required",
    },
    "Watchlist": {"company": "required", "universe": "optional"},
    "Screening": {"universe": "required", "company": "optional", "industry": "optional"},
    "Unknown": {
        "company": "required",
        "corporate_events": "optional",
        "industry": "optional",
    },
}

INTENT_TO_QUESTION_TYPE: dict[str, str] = {
    "Education": "education",
    "Valuation": "valuation",
    "Accounting": "financial_quality",
    "BusinessQuality": "business_quality",
    "Comparison": "comparison",
    "Industry": "sector",
    "Government": "macro",
    "Macro": "macro",
    "Portfolio": "portfolio",
    "Risk": "risk",
    "Research": "valuation",
    "Expectation": "forecast",
    "AlternativeData": "forecast",
    "Historical": "valuation",
    "Replay": "valuation",
    "Watchlist": "portfolio",
    "Screening": "sector",
    "Unknown": "valuation",
}
