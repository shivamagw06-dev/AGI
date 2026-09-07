"""Research Objective Engine (ROE) V1 — RQ1 Sprint 3 constitution."""

from __future__ import annotations

from typing import Any

ROE_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "ROE"
SPRINT = 3
SPRINT_NAME = "Research Objective Engine (ROE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.85
MAX_PLANNING_MS_TARGET = 30

PRIMARY_OBJECTIVES: tuple[str, ...] = (
    "Investment Evaluation",
    "Valuation Assessment",
    "Business Quality Assessment",
    "Financial Health Assessment",
    "Risk Assessment",
    "Portfolio Decision",
    "Sector Attractiveness",
    "Industry Structure",
    "Macro Impact",
    "Historical Analysis",
    "Peer Comparison",
    "Scenario Analysis",
    "Forecast",
    "News Impact",
    "Event Analysis",
    "Screening",
    "Educational",
    "Technical Analysis",
    "Accounting Review",
    "Management Assessment",
    "Ownership Review",
    "Governance Review",
    "Policy Analysis",
    "Regulatory Analysis",
)

# Alias used in product copy / examples
OBJECTIVE_ALIASES: dict[str, str] = {
    "Historical Valuation": "Historical Analysis",
    "Education": "Educational",
    "Portfolio Construction": "Portfolio Decision",
    "Valuation": "Valuation Assessment",
    "Risk": "Risk Assessment",
    "Business Quality": "Business Quality Assessment",
    "Financial Quality": "Financial Health Assessment",
    "Portfolio Suitability": "Portfolio Decision",
    "Sector Analysis": "Sector Attractiveness",
    "Sector": "Sector Attractiveness",
}

QUESTION_TYPES: tuple[str, ...] = (
    "Should I Buy?",
    "Should I Sell?",
    "Compare",
    "Analyse",
    "Explain",
    "Forecast",
    "Summarise",
    "Screen",
    "Monitor",
    "Stress Test",
    "Rebalance",
    "Teach",
    "Review",
    "Audit",
    "Diagnose",
)

DECISION_TYPES: tuple[str, ...] = (
    "Investment",
    "Portfolio",
    "Macro",
    "Company",
    "Sector",
    "Educational",
    "Operational",
)

RESEARCH_DEPTHS: tuple[str, ...] = (
    "Quick",
    "Standard",
    "Institutional",
    "Deep Research",
    "Continuous Monitoring",
)

URGENCIES: tuple[str, ...] = (
    "Live",
    "Today",
    "Near Term",
    "Long Term",
    "Evergreen",
)

EXPECTED_OUTPUTS: tuple[str, ...] = (
    "Brief",
    "Research Note",
    "Institutional Report",
    "Portfolio Memo",
    "Committee Memo",
    "Scenario Report",
    "Forecast Report",
    "Educational Guide",
    "Comparison Report",
    "Valuation Report",
    "Macro Report",
    "Risk Report",
    "Screening Report",
)

ALL_ANALYSTS: tuple[str, ...] = (
    "Business",
    "Financial",
    "Valuation",
    "Risk",
    "Committee",
    "Portfolio",
    "Forecast",
    "Sector",
    "Macro",
    "Evidence",
    "Peer",
    "Academy",
    "Accounting",
    "Management",
    "Ownership",
    "Governance",
    "Technical",
    "News",
    "Event",
)

ALL_LAYERS: tuple[str, ...] = (
    "FIL",
    "EIL",
    "PIL",
    "CIG",
    "FIE",
    "Management",
    "Portfolio",
    "Accounting",
    "Technical",
    "Macro",
    "Sector",
    "News",
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question",
    "primary_intent",
    "primary_objective",
    "secondary_objectives",
    "question_type",
    "decision_type",
    "research_depth",
    "urgency",
    "expected_output",
    "analysts",
    "layers",
    "apis",
    "blueprint",
    "routing_confidence",
    "requires_clarification",
    "executed_layers",
    "executed_analysts",
)


def normalize_objective(name: str | None) -> str | None:
    if not name:
        return None
    t = str(name).strip()
    if t in PRIMARY_OBJECTIVES:
        return t
    return OBJECTIVE_ALIASES.get(t, t if t in PRIMARY_OBJECTIVES else OBJECTIVE_ALIASES.get(t))


def constitution_dict() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ROE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "extends": "Intent Intelligence Engine / Research Ontology",
        "primary_question": "What institutional research objective should drive this workflow?",
        "law": "Determine the decision to support before collecting data or executing layers.",
        "exactly_one_primary_objective": True,
        "secondary_objectives_unlimited": True,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_planning_ms_target": MAX_PLANNING_MS_TARGET,
        "primary_objectives": list(PRIMARY_OBJECTIVES),
        "question_types": list(QUESTION_TYPES),
        "decision_types": list(DECISION_TYPES),
        "research_depths": list(RESEARCH_DEPTHS),
        "urgencies": list(URGENCIES),
        "expected_outputs": list(EXPECTED_OUTPUTS),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "success_criteria": {
            "primary_objective_accuracy": 0.99,
            "question_type_accuracy": 0.98,
            "blueprint_accuracy": 0.98,
            "analyst_routing_accuracy": 0.98,
            "layer_routing_accuracy": 0.98,
            "average_planning_ms": MAX_PLANNING_MS_TARGET,
            "benchmark_minimum": 1000,
        },
    }
